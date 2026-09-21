"""Create a repeatable local dataset for manual UI testing."""

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import delete, select

from src.database import create_db_engine, create_session_factory
from src.models import Reservation, ReservationState, Room, User


DEMO_PREFIX = "[DEMO]"


def get_or_create_user(session, name: str, email: str) -> User:
    user = session.scalar(select(User).where(User.email == email).limit(1))
    if user is None:
        user = User(name=name, email=email)
        session.add(user)
        session.flush()
    return user


def get_or_create_room(
    session, name: str, location: str, capacity: int
) -> Room:
    room = session.scalar(
        select(Room).where(
            Room.name == name,
            Room.location == location,
        ).limit(1)
    )
    if room is None:
        room = Room(name=name, location=location, capacity=capacity)
        session.add(room)
        session.flush()
    else:
        room.capacity = capacity
    return room


def at_hour(day, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)


def main():
    engine = create_db_engine()
    Session = create_session_factory(engine)

    try:
        with Session.begin() as session:
            current_user = session.get(User, 1)
            if current_user is None:
                current_user = get_or_create_user(
                    session, "Demo Student", "demo.student@example.com"
                )

            admin_user = get_or_create_user(
                session, "Demo Admin", "demo.admin@example.com"
            )

            room_a = get_or_create_room(
                session, "A101", "Library - Floor 1", 6
            )
            room_b = get_or_create_room(
                session, "B203", "Library - Floor 2", 12
            )
            room_c = get_or_create_room(
                session, "C310", "Science Building", 4
            )

            # Refresh only records owned by this seed script.
            session.execute(
                delete(Reservation).where(
                    Reservation.purpose.startswith(DEMO_PREFIX)
                )
            )

            demo_day = datetime.now(timezone.utc).date() + timedelta(days=1)
            session.add_all(
                [
                    Reservation(
                        user_id=current_user.id,
                        room_id=room_a.id,
                        start_time=at_hour(demo_day, 9),
                        end_time=at_hour(demo_day, 10),
                        number_of_people=3,
                        purpose=f"{DEMO_PREFIX} Group study - draft",
                        state=ReservationState.DRAFT,
                    ),
                    Reservation(
                        user_id=current_user.id,
                        room_id=room_a.id,
                        start_time=at_hour(demo_day, 11),
                        end_time=at_hour(demo_day, 12),
                        number_of_people=4,
                        purpose=f"{DEMO_PREFIX} Project meeting - confirmed",
                        state=ReservationState.CONFIRMED,
                    ),
                    Reservation(
                        user_id=current_user.id,
                        room_id=room_b.id,
                        start_time=at_hour(demo_day, 13),
                        end_time=at_hour(demo_day, 14),
                        number_of_people=8,
                        purpose=f"{DEMO_PREFIX} Cancelled booking",
                        state=ReservationState.CANCELLED,
                    ),
                    Reservation(
                        user_id=admin_user.id,
                        room_id=room_b.id,
                        start_time=at_hour(demo_day, 9),
                        end_time=at_hour(demo_day, 11),
                        number_of_people=10,
                        purpose=f"{DEMO_PREFIX} Other user confirmed booking",
                        state=ReservationState.CONFIRMED,
                    ),
                    Reservation(
                        user_id=current_user.id,
                        room_id=room_c.id,
                        start_time=at_hour(demo_day, 15),
                        end_time=at_hour(demo_day, 16),
                        number_of_people=2,
                        purpose=f"{DEMO_PREFIX} Small room draft",
                        state=ReservationState.DRAFT,
                    ),
                ]
            )

            current_user_id = current_user.id
            current_user_name = current_user.name

        print("Demo data is ready.")
        print(
            f"Current frontend user: {current_user_name} "
            f"(id={current_user_id})"
        )
        print(f"Demo reservation date (UTC): {demo_day.isoformat()}")
        print("Rooms: A101, B203, C310")
        if current_user_id != 1:
            print(
                "WARNING: frontend currently uses user id 1; update "
                "CURRENT_USER_ID in src/frontend/js/api.js to "
                f"{current_user_id}."
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
