from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.schema import CreateSchema, DropSchema

from src.database import Base, create_db_engine, create_session_factory
from src.models import Reservation, ReservationState, Room, User


def test_reservation_persists_in_postgresql():
    engine = create_db_engine()
    schema_name = f"c01_test_{uuid4().hex}"

    start_time = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)

    try:
        with engine.connect() as connection:
            assert connection.dialect.name == "postgresql"

            # Create an isolated namespace for this test.
            connection.execute(CreateSchema(schema_name))
            connection.commit()

            try:
                connection.execute(
                    text("SELECT set_config('search_path', :schema, false)"),
                    {"schema": schema_name},
                )
                Base.metadata.create_all(connection)
                connection.commit()

                Session = create_session_factory(connection)

                with Session() as session:
                    user = User(
                        name="Dat",
                        email="dat@example.com",
                    )
                    room = Room(
                        name="Study Room A",
                        location="Library, Floor 2",
                        capacity=6,
                    )

                    session.add_all([user, room])
                    session.commit()

                    user_id = user.id
                    room_id = room.id

                    reservation = Reservation(
                        user_id=user_id,
                        room_id=room_id,
                        start_time=start_time,
                        end_time=end_time,
                        number_of_people=4,
                        purpose="Software Engineering study",
                        state=ReservationState.DRAFT,
                    )

                    session.add(reservation)
                    session.flush()
                    reservation_id = reservation.id
                    session.commit()

                    # Remove all objects from the session's identity map.
                    session.expunge_all()

                # Query PostgreSQL using a new ORM session.
                with Session() as session:
                    loaded = session.get(Reservation, reservation_id)

                    assert loaded is not None
                    assert loaded is not reservation
                    assert loaded.id == reservation_id
                    assert loaded.user_id == user_id
                    assert loaded.room_id == room_id
                    assert loaded.start_time == start_time
                    assert loaded.end_time == end_time
                    assert loaded.number_of_people == 4
                    assert loaded.purpose == "Software Engineering study"
                    assert loaded.state == ReservationState.DRAFT

                    assert loaded.user.name == "Dat"
                    assert loaded.user.email == "dat@example.com"
                    assert loaded.room.name == "Study Room A"
                    assert loaded.room.location == "Library, Floor 2"
                    assert loaded.room.capacity == 6

            finally:
                # Remove only the schema created by this test.
                connection.rollback()
                connection.execute(
                    text("SELECT set_config('search_path', 'public', false)")
                )
                connection.execute(DropSchema(schema_name, cascade=True))
                connection.commit()
    finally:
        engine.dispose()