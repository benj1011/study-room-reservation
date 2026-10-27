"""v0.3: consent, FIFO, atomic cancellation and concurrent API writers."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Lock

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import src.main as api
from src import models
from src.migrate_v03 import upgrade
from test_baseline import baseline, create, payload, stored
from test_approval import approval, decide, read


def confirm(client, reservation):
    return client.post(f"/reservations/{reservation['id']}/confirm")


def test_join_requires_consent_and_never_writes_on_warning(baseline):
    client, Session, ids = baseline
    first = create(client, ids, join_queue=False)
    before = stored(Session)
    warning = client.post('/reservations', json=payload(ids, join_queue=False))
    assert warning.status_code == 409
    assert warning.json()['detail']['code'] == 'QUEUE_REQUIRED'
    assert stored(Session) == before
    second = create(client, ids, join_queue=True)
    assert first['queue_status'] == 'READY'
    assert (second['queue_status'], second['queue_ahead']) == ('WAITING', 1)
    assert 'join_queue' not in second
    assert confirm(client, second).status_code == 409
    assert read(client, second)['state'] == 'DRAFT'


def test_confirm_cancels_waiters_with_persistent_reason(baseline):
    client, Session, ids = baseline
    first, second, third = [create(client, ids) for _ in range(3)]
    assert confirm(client, first).status_code == 200
    for waiting in [second, third]:
        saved = read(client, waiting)
        assert saved['state'] == 'CANCELLED'
        assert saved['cancellation_reason'] == 'Another request confirmed.'
        assert saved['queue_status'] == 'NONE'
    with Session() as db:
        assert db.get(models.Reservation, second['id']).cancellation_reason == 'Another request confirmed.'
    assert client.post(f"/reservations/{first['id']}/cancel").status_code == 200
    assert read(client, second)['state'] == 'CANCELLED'  # Never resurrect a cancelled waiter.


def test_cancelling_head_promotes_without_auto_confirmation(baseline):
    client, Session, ids = baseline
    first, second, third = [create(client, ids) for _ in range(3)]
    assert client.post(f"/reservations/{first['id']}/cancel").status_code == 200
    assert read(client, second)['queue_status'] == 'READY'
    assert read(client, second)['state'] == 'DRAFT'
    assert read(client, third)['queue_ahead'] == 1
    assert confirm(client, third).status_code == 409
    assert confirm(client, second).status_code == 200
    assert read(client, third)['state'] == 'CANCELLED'


@pytest.mark.parametrize('start,end,overlap', [
    ('09:00', '10:00', False), ('09:30', '10:30', True),
    ('10:00', '11:00', True), ('10:30', '11:30', True), ('11:00', '12:00', False),
])
def test_half_open_intervals_and_auto_cancel_scope(baseline, start, end, overlap):
    client, Session, ids = baseline
    first = create(client, ids)
    second = create(client, ids, start=start, end=end)
    assert second['queue_status'] == ('WAITING' if overlap else 'READY')
    assert confirm(client, first).status_code == 200
    assert read(client, second)['state'] == ('CANCELLED' if overlap else 'DRAFT')


def test_other_room_and_nontransitive_overlap_are_not_cancelled(baseline):
    client, Session, ids = baseline
    first = create(client, ids, start='09:00', end='10:00')
    middle = create(client, ids, start='09:30', end='10:30')
    last = create(client, ids, start='10:00', end='11:00')
    other = create(client, ids, room_id=ids[2], number_of_people=1, start='09:00', end='10:00')
    assert confirm(client, first).status_code == 200
    assert read(client, middle)['state'] == 'CANCELLED'
    assert read(client, last)['queue_status'] == 'READY'
    assert read(client, other)['state'] == 'DRAFT'
    assert confirm(client, last).status_code == 200


@pytest.mark.parametrize('approved', [False, True])
def test_pending_head_blocks_then_rejection_or_expiry_releases(approval, approved):
    client, Session, ids, approver, clock = approval
    interval = dict(start_time='2030-10-02T10:00:00Z', end_time='2030-10-02T11:00:00Z')
    first = create(client, ids, **interval)
    clock[0] += timedelta(hours=1)
    second = create(client, ids, **interval)
    assert decide(client, second, approver).status_code == 200
    assert confirm(client, second).status_code == 409
    if approved:
        assert decide(client, first, approver).status_code == 200
        clock[0] = datetime.fromisoformat(first['approval_deadline'])
    else:
        assert decide(client, first, approver, 'REJECTED').status_code == 200
    assert read(client, second)['queue_status'] == 'READY'
    assert confirm(client, second).status_code == 200


def test_reduced_capacity_head_does_not_block_eligible_waiter(baseline):
    client, Session, ids = baseline
    first = create(client, ids, number_of_people=6)
    second = create(client, ids, number_of_people=2)
    with Session() as db:
        db.get(models.Room, ids[1]).capacity = 3
        db.commit()
    assert read(client, first)['queue_status'] == 'INACTIVE'
    assert confirm(client, second).status_code == 200


def test_start_boundary_expires_draft_without_writing_on_read(baseline, monkeypatch):
    client, Session, ids = baseline
    first = create(client, ids)
    monkeypatch.setattr(models, 'utc_now', lambda: datetime.fromisoformat(first['start_time']))
    assert read(client, first)['queue_status'] == 'EXPIRED'
    assert read(client, first)['state'] == 'DRAFT'
    assert confirm(client, first).status_code == 409


def test_queue_opt_in_rechecks_confirmed_booking(baseline):
    client, Session, ids = baseline
    first = create(client, ids)
    assert client.post('/reservations', json=payload(ids, join_queue=False)).status_code == 409
    assert confirm(client, first).status_code == 200
    before = stored(Session)
    response = client.post('/reservations', json=payload(ids, join_queue=True))
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'ROOM_BOOKED'
    assert stored(Session) == before


def test_confirmation_failure_rolls_back_winner_and_waiters(baseline, monkeypatch):
    client, Session, ids = baseline
    first, second = create(client, ids), create(client, ids)
    before = stored(Session)
    def fail_commit(self):
        self.flush()  # Execute updates in PostgreSQL, then fail before commit.
        raise IntegrityError('commit', {}, Exception('injected failure'))
    with monkeypatch.context() as m:
        m.setattr(Session.class_, 'commit', fail_commit)
        assert confirm(client, first).status_code == 409
    assert stored(Session) == before
    assert read(client, second)['cancellation_reason'] is None
    assert confirm(client, first).status_code == 200


def run_competing(monkeypatch, operations):
    original = api.lock_room
    barrier = Barrier(2, timeout=10)
    pids, mutex = set(), Lock()
    def synchronize(db, room_id):
        with mutex:
            pids.add(db.scalar(text('SELECT pg_backend_pid()')))
        barrier.wait()
        return original(db, room_id)
    monkeypatch.setattr(api, 'lock_room', synchronize)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(operation) for operation in operations]
        results = [future.result(timeout=15) for future in futures]
    assert len(pids) == 2
    return results


def test_concurrent_creates_warn_second_without_silent_queue(baseline, monkeypatch):
    client, Session, ids = baseline
    responses = run_competing(monkeypatch, [
        lambda: client.post('/reservations', json=payload(ids, join_queue=False)),
        lambda: client.post('/reservations', json=payload(ids, join_queue=False)),
    ])
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert len(stored(Session)) == 1


def test_create_racing_confirm_never_leaves_conflicting_live_draft(baseline, monkeypatch):
    client, Session, ids = baseline
    first = create(client, ids)
    created, confirmed = run_competing(monkeypatch, [
        lambda: client.post('/reservations', json=payload(ids, join_queue=True)),
        lambda: confirm(client, first),
    ])
    assert confirmed.status_code == 200
    assert created.status_code in (201, 409)
    assert all(row[-1] != 'DRAFT' for row in stored(Session))


def test_v03_migration_preserves_history_and_is_repeatable(baseline):
    client, Session, ids = baseline
    first, second = create(client, ids), create(client, ids)
    before = stored(Session)
    with Session() as db:
        db.execute(text('ALTER TABLE reservations DROP COLUMN cancellation_reason'))
        db.commit()
        for _ in range(2):
            upgrade(db.connection())
            db.commit()
    assert stored(Session) == before
    assert read(client, second)['queue_status'] == 'WAITING'
    assert confirm(client, first).status_code == 200
    assert read(client, second)['cancellation_reason'] == 'Another request confirmed.'


def test_frontend_origin_is_allowed(baseline):
    client, _, _ = baseline
    response = client.options('/reservations', headers={
        'Origin': 'http://localhost:5001', 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5001'


def test_legacy_draft_over_confirmed_booking_is_blocked_not_ready(baseline):
    client, Session, ids = baseline
    first, second = create(client, ids), create(client, ids)
    # Reproduce a v0.2 database where Create was allowed over a confirmed booking.
    with Session() as db:
        db.get(models.Reservation, first['id']).state = models.ReservationState.CONFIRMED
        db.commit()
    assert read(client, second)['queue_status'] == 'BLOCKED'
    assert confirm(client, second).status_code == 409
    assert client.post(f"/reservations/{first['id']}/cancel").status_code == 200
    assert read(client, second)['queue_status'] == 'READY'


def test_queue_context_includes_other_users_without_exposing_details(baseline):
    client, Session, ids = baseline
    create(client, ids)
    other_user = client.post('/users', json={'name': 'Second', 'email': 'second@example.test'}).json()['id']
    waiting = create(client, ids, user_id=other_user)
    response = client.get('/reservations', params={'user_id': other_user}).json()
    assert len(response) == 1
    assert response[0]['id'] == waiting['id']
    assert response[0]['queue_ahead'] == 1
    assert response[0]['queue_status'] == 'WAITING'
    assert 'predecessor' not in response[0]
