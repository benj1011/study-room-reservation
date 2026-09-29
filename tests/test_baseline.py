"""C02 operation acceptance examples against isolated real PostgreSQL schemas."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.schema import CreateSchema, DropSchema

from src.database import Base, create_db_engine, create_session_factory
from src.main import app, get_db
from src.models import Reservation, ReservationState, Room, User
import src.main as api


@pytest.fixture
def baseline():
    admin = create_db_engine()
    schema = f"c02_test_{uuid4().hex}"
    with admin.begin() as connection:
        assert connection.dialect.name == "postgresql"
        connection.execute(CreateSchema(schema))
    engine = create_engine(admin.url, connect_args={"options": f"-csearch_path={schema}"})
    Session = create_session_factory(engine)
    previous_overrides = app.dependency_overrides.copy()
    try:
        Base.metadata.create_all(engine)
        with Session() as db:
            user = User(name="C02 Student", email="c02@example.test")
            room = Room(name="A101", location="Library", capacity=6)
            other = Room(name="B201", location="Library", capacity=2)
            db.add_all([user, room, other])
            db.commit()
            ids = user.id, room.id, other.id

        def get_test_db():
            with Session() as db:
                try:
                    yield db
                except Exception:
                    db.rollback()
                    raise

        app.dependency_overrides[get_db] = get_test_db
        with TestClient(app) as client:
            yield client, Session, ids
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def payload(ids, start="10:00", end="11:00", **changes):
    result = dict(user_id=ids[0], room_id=ids[1],
                  start_time=f"2030-10-01T{start}:00+00:00",
                  end_time=f"2030-10-01T{end}:00+00:00",
                  number_of_people=4, purpose="C02 acceptance example")
    result.update(changes)
    return result


def create(client, ids, **changes):
    response = client.post('/reservations', json=payload(ids, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def available(client, start="10:00", end="11:00", people=4):
    return client.get('/rooms/available', params={
        'start_time': f'2030-10-01T{start}:00+00:00',
        'end_time': f'2030-10-01T{end}:00+00:00', 'people': people})


def stored(Session):
    with Session() as db:
        return [(r.id, r.user_id, r.room_id, r.start_time, r.end_time,
                 r.number_of_people, r.purpose, r.state.value)
                for r in db.scalars(select(Reservation).order_by(Reservation.id))]


def test_create_durable_draft_without_allocation(baseline):
    client, Session, ids = baseline
    before = available(client).json()
    reservation = create(client, ids)
    assert reservation['state'] == 'DRAFT'
    assert stored(Session)[0][-1] == 'DRAFT'
    assert available(client).json() == before
    second = create(client, ids)
    assert second['id'] != reservation['id']
    assert available(client).json() == before


@pytest.mark.parametrize('changes,status', [
    ({'end_time': '2030-10-01T10:00:00Z'}, 422),
    ({'end_time': '2030-10-01T09:00:00Z'}, 422),
    ({'start_time': '2030-10-01T10:00:00'}, 422),
    ({'start_time': None}, 422),
    ({'number_of_people': 0}, 422),
    ({'number_of_people': 7}, 422),
    ({'purpose': '  '}, 422),
    ({'room_id': 999999}, 404),
    ({'user_id': 999999}, 404),
])
def test_create_rejection_has_no_write(baseline, changes, status):
    client, Session, ids = baseline
    before = stored(Session)
    response = client.post('/reservations', json=payload(ids, **changes))
    assert response.status_code == status
    assert stored(Session) == before


def test_availability_boundaries_blocking_and_capacity(baseline):
    client, Session, ids = baseline
    r = create(client, ids)
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 200
    for start, end, expected in [('09:00','10:00',True), ('10:30','11:30',False),
                                 ('11:00','12:00',True)]:
        response = available(client, start, end)
        assert response.status_code == 200
        assert (ids[1] in [x['id'] for x in response.json()]) == expected
    before = stored(Session)
    assert available(client, people=7).json() == []
    assert [r['id'] for r in available(client, people=1).json()] == [ids[2]]
    assert stored(Session) == before
    assert client.post(f"/reservations/{r['id']}/cancel").status_code == 200
    assert [x['id'] for x in available(client).json()] == [ids[1]]


@pytest.mark.parametrize('start,end,people', [('10:00','10:00',1),
                                               ('11:00','10:00',1),
                                               ('10:00','11:00',0)])
def test_availability_invalid_query(baseline, start, end, people):
    client, Session, ids = baseline
    create(client, ids)
    before = stored(Session)
    assert available(client, start, end, people).status_code == 422
    assert stored(Session) == before


def test_confirm_success_conflict_and_adjacent_interval(baseline):
    client, Session, ids = baseline
    first = create(client, ids)
    result = client.post(f"/reservations/{first['id']}/confirm")
    assert result.status_code == 200
    assert result.json()['state'] == 'CONFIRMED'
    second = create(client, ids)  # Create is allowed even over a confirmed booking.
    before = stored(Session)
    assert client.post(f"/reservations/{second['id']}/confirm").status_code == 409
    assert stored(Session) == before
    adjacent = create(client, ids, start='11:00', end='12:00')
    assert client.post(f"/reservations/{adjacent['id']}/confirm").status_code == 200
    assert [r[-1] for r in stored(Session)] == ['CONFIRMED','DRAFT','CONFIRMED']


def test_confirm_rechecks_capacity(baseline):
    client, Session, ids = baseline
    r = create(client, ids)
    with Session() as db:
        db.get(Room, ids[1]).capacity = 2
        db.commit()
    before = stored(Session)
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 422
    assert stored(Session) == before


@pytest.mark.parametrize('state', ['CONFIRMED', 'CANCELLED'])
def test_confirm_invalid_source_state(baseline, state):
    client, Session, ids = baseline
    r = create(client, ids)
    operation = 'confirm' if state == 'CONFIRMED' else 'cancel'
    assert client.post(f"/reservations/{r['id']}/{operation}").status_code == 200
    before = stored(Session)
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 409
    assert stored(Session) == before


@pytest.mark.parametrize('confirmed', [False, True])
def test_cancel_retains_details_releases_allocation_and_rejects_repeat(baseline, confirmed):
    client, Session, ids = baseline
    r = create(client, ids)
    if confirmed:
        assert client.post(f"/reservations/{r['id']}/confirm").status_code == 200
    before = stored(Session)[0]
    response = client.post(f"/reservations/{r['id']}/cancel")
    assert response.status_code == 200
    after = stored(Session)[0]
    assert after[:-1] == before[:-1]
    assert after[-1] == 'CANCELLED'
    assert client.get(f"/reservations/{r['id']}").json()['state'] == 'CANCELLED'
    assert [x['id'] for x in available(client).json()] == [ids[1]]
    assert client.post(f"/reservations/{r['id']}/cancel").status_code == 409
    assert stored(Session)[0] == after
    replacement = create(client, ids)
    assert client.post(f"/reservations/{replacement['id']}/confirm").status_code == 200


@pytest.mark.parametrize('operation', ['confirm', 'cancel'])
def test_missing_reservation(baseline, operation):
    client, Session, ids = baseline
    assert client.post(f'/reservations/999999/{operation}').status_code == 404
    assert stored(Session) == []


def simultaneous(monkeypatch, client, operations):
    """Synchronize independent DB sessions immediately before room locking."""
    rendezvous = Barrier(2, timeout=10)
    pids = set()
    mutex = Lock()
    original = api.lock_reservation_room

    def synchronize(db, reservation_id):
        pid = db.scalar(text('SELECT pg_backend_pid()'))
        with mutex:
            pids.add(pid)
        rendezvous.wait()
        return original(db, reservation_id)

    monkeypatch.setattr(api, 'lock_reservation_room', synchronize)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, path) for path in operations]
        results = [future.result(timeout=15) for future in futures]
    assert len(pids) == 2, 'Concurrency evidence requires separate PostgreSQL sessions'
    return results


@pytest.mark.parametrize('attempt', range(3))
def test_concurrent_confirms_allocate_at_most_once(baseline, monkeypatch, attempt):
    client, Session, ids = baseline
    one, two = create(client, ids), create(client, ids)
    results = simultaneous(monkeypatch, client,
        [f"/reservations/{r['id']}/confirm" for r in [one, two]])
    assert sorted(r.status_code for r in results) == [200,409]
    assert sorted(r[-1] for r in stored(Session)) == ['CONFIRMED','DRAFT']


@pytest.mark.parametrize('attempt', range(3))
def test_concurrent_confirm_cancel_never_resurrects(baseline, monkeypatch, attempt):
    client, Session, ids = baseline
    r = create(client, ids)
    confirm, cancel = simultaneous(monkeypatch, client,
        [f"/reservations/{r['id']}/{op}" for op in ['confirm','cancel']])
    assert confirm.status_code in (200,409)
    assert cancel.status_code == 200
    assert stored(Session)[0][-1] == 'CANCELLED'


def test_cancel_past_interval_has_no_deadline(baseline):
    client, Session, ids = baseline
    r = create(client, ids, start_time='2000-01-01T10:00:00Z',
               end_time='2000-01-01T11:00:00Z')
    assert client.post(f"/reservations/{r['id']}/confirm").status_code == 200
    before = stored(Session)[0]
    assert client.post(f"/reservations/{r['id']}/cancel").status_code == 200
    after = stored(Session)[0]
    assert after[:-1] == before[:-1]
    assert after[-1] == 'CANCELLED'
