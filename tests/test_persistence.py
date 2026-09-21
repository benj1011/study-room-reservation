"""C01 spike: create a reservation through the API and reload it from PostgreSQL."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.schema import CreateSchema, DropSchema

from src.database import Base, create_db_engine, create_session_factory
from src.main import app, get_db
from src.models import Reservation, ReservationState, Room, User


def test_reservation_persists_in_postgresql():
    """POST a reservation, then load and verify it in a new DB session."""
    engine = create_db_engine()
    schema_name = f"c01_test_{uuid4().hex}"

    try:
        with engine.connect() as connection:
            assert connection.dialect.name == "postgresql"
            connection.execute(CreateSchema(schema_name))
            connection.execute(
                text("SELECT set_config('search_path', :schema, false)"),
                {"schema": schema_name},
            )
            connection.commit()
            Base.metadata.create_all(connection)
            connection.commit()

            Session = create_session_factory(connection)

            try:
                # A reservation needs an existing user and room.
                with Session() as session:
                    user = User(name="Dat", email="dat@example.com")
                    room = Room(
                        name="A101",
                        location="Library, Floor 2",
                        capacity=6,
                    )
                    session.add_all([user, room])
                    session.commit()
                    user_id = user.id
                    room_id = room.id

                def override_get_db():
                    with Session() as session:
                        yield session

                app.dependency_overrides[get_db] = override_get_db

                start_time = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
                end_time = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)

                response = TestClient(app).post(
                    "/reservations",
                    json={
                        "user_id": user_id,
                        "room_id": room_id,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "number_of_people": 4,
                        "purpose": "Software Engineering study",
                    },
                )

                assert response.status_code == 201
                response_data = response.json()
                assert isinstance(response_data["id"], int)
                assert response_data["state"] == "DRAFT"
                reservation_id = response_data["id"]

                # A new ORM session proves that the API committed to PostgreSQL.
                with Session() as verification_session:
                    loaded = verification_session.get(Reservation, reservation_id)

                    assert loaded is not None
                    assert loaded.id == reservation_id
                    assert loaded.user_id == user_id
                    assert loaded.room_id == room_id
                    assert loaded.start_time == start_time
                    assert loaded.end_time == end_time
                    assert loaded.number_of_people == 4
                    assert loaded.purpose == "Software Engineering study"
                    assert loaded.state == ReservationState.DRAFT
                    assert loaded.user.name == "Dat"
                    assert loaded.room.name == "A101"
            finally:
                app.dependency_overrides.clear()
                connection.rollback()
                connection.execute(
                    text("SELECT set_config('search_path', 'public', false)")
                )
                connection.execute(DropSchema(schema_name, cascade=True))
                connection.commit()
    finally:
        engine.dispose()
