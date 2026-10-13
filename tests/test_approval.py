"""Part B.14: v0.2 approval behavior and ordinary-room regression support."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src import models
from src.migrate_v02 import upgrade
from test_baseline import baseline, create, payload, stored, available, simultaneous


@pytest.fixture
def approval(baseline, monkeypatch):
    client, Session, ids = baseline
    clock = [datetime(2030, 9, 30, 10, 0, tzinfo=timezone.utc)]
    monkeypatch.setattr(models, 'utc_now', lambda: clock[0])
    approver = client.post('/users', json={'name':'Approver','email':'approver@example.test'}).json()['id']
    response = client.post('/rooms', json={'name':'Protected','location':'Library','capacity':6,
                                         'requires_approval':True,'approver_user_id':approver})
    assert response.status_code == 201
    protected_ids = ids[0], response.json()['id'], ids[2]
    return client, Session, protected_ids, approver, clock


def decide(client, reservation, approver, decision='APPROVED'):
    return client.post(f"/reservations/{reservation['id']}/approve",
                       json={'decision':decision}, headers={'X-User-Id':str(approver)})


def read(client, reservation):
    return client.get(f"/reservations/{reservation['id']}").json()


def test_approval_is_permission_not_allocation(approval):
    client, Session, ids, approver, clock = approval
    r = create(client, ids)
    assert r['state'] == 'DRAFT'
    assert r['approval_status'] == 'PENDING'
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 409
    response = decide(client, r, approver)
    assert response.status_code == 200
    approved = response.json()
    assert approved['state'] == 'DRAFT'
    assert approved['approval_status'] == 'APPROVED'
    assert approved['decided_by'] == approver
    assert datetime.fromisoformat(approved['decided_at']) == clock[0]
    assert ids[1] in [x['id'] for x in available(client).json()]
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 200
    assert ids[1] not in [x['id'] for x in available(client).json()]
    with Session() as db:
        saved = db.get(models.Reservation, r['id'])
        assert saved.approval_decision == models.ApprovalStatus.APPROVED
        assert saved.decided_by == approver


@pytest.mark.parametrize('identity,status', [('missing',401),('wrong',403),('unknown',403)])
def test_only_assigned_approver_can_decide(approval, identity, status):
    client, Session, ids, approver, clock = approval
    r = create(client, ids)
    headers = {} if identity == 'missing' else {'X-User-Id':str(ids[0] if identity == 'wrong' else 999999)}
    before = read(client,r)
    response = client.post(f"/reservations/{r['id']}/approve", json={'decision':'APPROVED'},headers=headers)
    assert response.status_code == status
    assert read(client,r) == before


def test_reject_cannot_confirm_but_can_cancel(approval):
    client, Session, ids, approver, clock = approval
    r = create(client, ids)
    response = decide(client,r,approver,'REJECTED')
    assert response.status_code == 200
    assert response.json()['approval_status'] == 'REJECTED'
    before = read(client,r)
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 409
    assert decide(client,r,approver).status_code == 409
    assert read(client,r) == before
    assert ids[1] in [x['id'] for x in available(client).json()]
    assert client.post(f"/reservations/{r['id']}/cancel").status_code == 200


@pytest.mark.parametrize('approved', [False,True])
@pytest.mark.parametrize('offset,expected', [(-1,200),(0,409),(1,409)])
def test_deadline_boundary_on_confirm_or_approve(approval, approved, offset, expected):
    client, Session, ids, approver, clock = approval
    r = create(client,ids)
    if approved:
        assert decide(client,r,approver).status_code == 200
    clock[0] = datetime.fromisoformat(r['approval_deadline']) + timedelta(microseconds=offset)
    before = read(client,r)
    response = (client.post(f"/reservations/{r['id']}/confirm") if approved
                else decide(client,r,approver))
    assert response.status_code == expected
    if expected == 409:
        assert read(client,r) == before
        assert before['state'] == 'DRAFT'
        assert before['approval_status'] == 'EXPIRED'
    else:
        assert response.json()['approval_status'] == 'APPROVED'


def test_deadline_minimum_and_protected_past_start(approval):
    client, Session, ids, approver, clock = approval
    for hours in [2,48]:
        start = clock[0] + timedelta(hours=hours)
        r = create(client,ids,start_time=start.isoformat(),end_time=(start+timedelta(hours=1)).isoformat())
        assert datetime.fromisoformat(r['approval_deadline']) == clock[0]+timedelta(hours=min(hours,24))
    before = stored(Session)
    response=client.post('/reservations',json=payload(ids,start_time=clock[0].isoformat(),
        end_time=(clock[0]+timedelta(hours=1)).isoformat()))
    assert response.status_code == 422
    assert stored(Session) == before


def test_confirmed_allocation_survives_approval_deadline(approval):
    client, Session, ids, approver, clock = approval
    r=create(client,ids)
    assert decide(client,r,approver).status_code == 200
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 200
    clock[0] += timedelta(days=2)
    assert read(client,r)['state'] == 'CONFIRMED'
    assert read(client,r)['approval_status'] == 'APPROVED'
    assert ids[1] not in [x['id'] for x in available(client).json()]


def test_delayed_approval_does_not_override_new_conflict(approval):
    client, Session, ids, approver, clock = approval
    first, second = create(client,ids), create(client,ids)
    assert decide(client,first,approver).status_code == 200
    assert client.post(f"/reservations/{first['id']}/confirm").status_code == 200
    clock[0] += timedelta(hours=1)
    assert decide(client,second,approver).status_code == 200
    assert client.post(f"/reservations/{second['id']}/confirm").status_code == 409
    assert read(client,second)['state'] == 'DRAFT'


@pytest.mark.parametrize('status', ['PENDING','APPROVED','EXPIRED'])
def test_cancel_approval_states_prevents_later_decisions(approval,status):
    client, Session, ids, approver, clock = approval
    r=create(client,ids)
    if status == 'APPROVED':
        assert decide(client,r,approver).status_code == 200
    if status == 'EXPIRED':
        clock[0] += timedelta(days=1)
    assert client.post(f"/reservations/{r['id']}/cancel").status_code == 200
    assert decide(client,r,approver).status_code == 409
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 409


def test_repeated_decision_and_invalid_input(approval):
    client, Session, ids, approver, clock = approval
    r=create(client,ids)
    assert decide(client,r,approver,'INVALID').status_code == 422
    assert decide(client,{'id':999999},approver).status_code == 404
    assert decide(client,r,approver).status_code == 200
    before=read(client,r)
    assert decide(client,r,approver).status_code == 409
    assert decide(client,r,approver,'REJECTED').status_code == 409
    assert read(client,r) == before


def test_room_policy_validation(approval):
    client, Session, ids, approver, clock = approval
    base={'name':'Bad','location':'Library','capacity':6}
    assert client.post('/rooms',json={**base,'requires_approval':True}).status_code == 422
    assert client.post('/rooms',json={**base,'approver_user_id':approver}).status_code == 422
    assert client.post('/rooms',json={**base,'requires_approval':True,'approver_user_id':999999}).status_code == 404


def test_concurrent_approved_confirms_still_exclusive(approval,monkeypatch):
    client, Session, ids, approver, clock = approval
    one,two=create(client,ids),create(client,ids)
    for r in [one,two]:
        assert decide(client,r,approver).status_code == 200
    results=simultaneous(monkeypatch,client,[f"/reservations/{r['id']}/confirm" for r in [one,two]])
    assert sorted(r.status_code for r in results) == [200,409]
    assert sorted(r[-1] for r in stored(Session)) == ['CONFIRMED','DRAFT']


@pytest.mark.parametrize('competitor', ['cancel','confirm','reject'])
def test_approval_races(approval,monkeypatch,competitor):
    client, Session, ids, approver, clock = approval
    r=create(client,ids)
    # Reuse the two-session barrier while adding request bodies/identity.
    class Requests:
        def post(self,path):
            if path.endswith('/approve') or path.endswith('/reject'):
                decision='REJECTED' if path.endswith('/reject') else 'APPROVED'
                return decide(client,r,approver,decision)
            return client.post(path)
    approve,other=simultaneous(monkeypatch,Requests(),
        [f"/reservations/{r['id']}/approve", f"/reservations/{r['id']}/{competitor}"])
    final=read(client,r)
    if competitor == 'cancel':
        assert approve.status_code in (200,409)
        assert other.status_code == 200
        assert final['state'] == 'CANCELLED'
    elif competitor == 'confirm':
        assert approve.status_code == 200
        assert other.status_code in (200,409)
        assert final['state'] == ('CONFIRMED' if other.status_code == 200 else 'DRAFT')
    else:
        assert sorted([approve.status_code,other.status_code]) == [200,409]
        assert final['approval_status'] == ('APPROVED' if approve.status_code == 200 else 'REJECTED')


def test_migration_preserves_v01_records_and_is_repeatable(baseline):
    client, Session, ids=baseline
    r=create(client,ids)
    with Session() as db:
        # Reconstruct the v0.1 shape in this test's isolated schema only.
        db.execute(text('ALTER TABLE rooms DROP COLUMN requires_approval, DROP COLUMN approver_user_id'))
        db.execute(text('''ALTER TABLE reservations DROP COLUMN approval_decision,
            DROP COLUMN approval_deadline, DROP COLUMN decided_by, DROP COLUMN decided_at'''))
        db.execute(text('DROP TYPE approval_status'))
        db.commit()
        upgrade(db.connection())
        db.commit()
        upgrade(db.connection())
        db.commit()
    result=read(client,r)
    assert result['id'] == r['id']
    assert result['state'] == 'DRAFT'
    assert result['approval_status'] == 'NOT_REQUIRED'
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 200


def test_client_cannot_supply_its_own_approval(approval):
    client, Session, ids, approver, clock = approval
    r=create(client,ids,approval_decision='APPROVED',approval_status='APPROVED',
             decided_by=approver,decided_at=clock[0].isoformat(),
             approval_deadline='2099-01-01T00:00:00Z',state='CONFIRMED')
    assert r['state'] == 'DRAFT'
    assert r['approval_status'] == 'PENDING'
    assert r['decided_by'] is None
    assert r['decided_at'] is None
    assert datetime.fromisoformat(r['approval_deadline']) == clock[0]+timedelta(hours=24)
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 409


def test_expiry_is_read_only_and_does_not_block_room(approval):
    client, Session, ids, approver, clock = approval
    r=create(client,ids)
    assert decide(client,r,approver).status_code == 200
    clock[0] += timedelta(days=1)
    assert read(client,r)['approval_status'] == 'EXPIRED'
    listed=client.get('/reservations').json()
    assert next(item for item in listed if item['id']==r['id'])['approval_status']=='EXPIRED'
    assert ids[1] in [x['id'] for x in available(client).json()]
    with Session() as db:
        saved=db.get(models.Reservation,r['id'])
        assert saved.approval_decision == models.ApprovalStatus.APPROVED
        assert saved.state == models.ReservationState.DRAFT
        assert saved.decided_by == approver


def test_confirm_evaluates_deadline_after_room_lock(approval, monkeypatch):
    """C05 DD-03: crossing the deadline during serialization invalidates approval.

    Advance a controlled clock at the real lock boundary; existing concurrent
    tests separately verify contention with independent PostgreSQL sessions.
    """
    import src.main as api

    client, Session, ids, approver, clock = approval
    reservation = create(client, ids)
    assert decide(client, reservation, approver).status_code == 200
    deadline = datetime.fromisoformat(reservation['approval_deadline'])
    clock[0] = deadline - timedelta(microseconds=1)
    original_lock = api.lock_reservation_room
    acquired = []
    with Session() as db:
        row = db.get(models.Reservation, reservation['id'])
        before = (row.state, row.approval_decision, row.decided_by, row.decided_at)

    def cross_deadline_after_lock(db, reservation_id):
        result = original_lock(db, reservation_id)
        acquired.append(reservation_id)
        clock[0] = deadline
        return result

    monkeypatch.setattr(api, 'lock_reservation_room', cross_deadline_after_lock)
    response = client.post(f"/reservations/{reservation['id']}/confirm")
    assert acquired == [reservation['id']]
    assert response.status_code == 409
    assert read(client, reservation)['approval_status'] == 'EXPIRED'
    with Session() as db:
        row = db.get(models.Reservation, reservation['id'])
        assert (row.state, row.approval_decision, row.decided_by, row.decided_at) == before
