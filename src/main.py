"""FastAPI endpoints using the PostgreSQL persistence layer from main."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.database import create_db_engine, create_session_factory
from src.models import Reservation, ReservationState, Room, User
from src.schemas import (
    ReservationCreate, ReservationRead, RoomCreate, RoomRead, UserCreate, UserRead,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_db_engine()
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="Study Room Reservation API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise


DB = Annotated[Session, Depends(get_db)]


def save(db: Session, record):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Data conflicts with database constraints") from exc
    db.refresh(record)
    return record


def require_reservation(db: Session, reservation_id: int):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(404, "Reservation not found")
    return reservation


@app.get("/")
def root():
    return {"message": "Study Room Reservation API is running"}


@app.get("/users", response_model=list[UserRead])
def get_users(db: DB):
    return db.scalars(select(User).order_by(User.id)).all()


@app.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: DB):
    user = User(**payload.model_dump())
    db.add(user)
    return save(db, user)


@app.get("/rooms", response_model=list[RoomRead])
def get_rooms(db: DB):
    return db.scalars(select(Room).order_by(Room.id)).all()


@app.post("/rooms", response_model=RoomRead, status_code=201)
def create_room(payload: RoomCreate, db: DB):
    room = Room(**payload.model_dump())
    db.add(room)
    return save(db, room)


@app.get("/rooms/available", response_model=list[RoomRead])
def get_available_rooms(
    db: DB,
    start_time: AwareDatetime,
    end_time: AwareDatetime,
    people: Annotated[int, Query(gt=0)] = 1,
):
    if end_time <= start_time:
        raise HTTPException(422, "End time must be after start time")
    conflict = select(Reservation.id).where(
        Reservation.room_id == Room.id,
        Reservation.state == ReservationState.CONFIRMED,
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    ).exists()
    return db.scalars(
        select(Room).where(Room.capacity >= people, ~conflict).order_by(Room.id)
    ).all()


@app.get("/reservations", response_model=list[ReservationRead])
def get_reservations(db: DB, user_id: Annotated[int | None, Query(gt=0)] = None):
    query = (
        select(Reservation)
        .options(selectinload(Reservation.room))
        .order_by(Reservation.id)
    )
    if user_id is not None:
        query = query.where(Reservation.user_id == user_id)
    return db.scalars(query).all()


@app.get("/reservations/{reservation_id}", response_model=ReservationRead)
def get_reservation(reservation_id: int, db: DB):
    reservation = db.scalar(
        select(Reservation)
        .options(selectinload(Reservation.room))
        .where(Reservation.id == reservation_id)
    )
    if reservation is None:
        raise HTTPException(404, "Reservation not found")
    return reservation


@app.post("/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(payload: ReservationCreate, db: DB):
    if db.get(User, payload.user_id) is None:
        raise HTTPException(404, "User not found")
    room = db.get(Room, payload.room_id)
    if room is None:
        raise HTTPException(404, "Room not found")
    if payload.number_of_people > room.capacity:
        raise HTTPException(422, f"Room capacity is {room.capacity} people")
    reservation = Reservation(**payload.model_dump(), state=ReservationState.DRAFT)
    db.add(reservation)
    return save(db, reservation)


def lock_reservation_room(db: Session, reservation_id: int):
    reservation = require_reservation(db, reservation_id)
    # All state transitions lock the same room first. PostgreSQL's default
    # READ COMMITTED isolation lets the next query see the preceding commit.
    room = db.scalar(select(Room).where(Room.id == reservation.room_id).with_for_update())
    if room is None:
        raise HTTPException(404, "Room not found")
    # The reservation may have changed while this request waited for the lock.
    db.refresh(reservation)
    return reservation, room


@app.post("/reservations/{reservation_id}/confirm", response_model=ReservationRead)
def confirm_reservation(reservation_id: int, db: DB):
    reservation, room = lock_reservation_room(db, reservation_id)
    if reservation.state != ReservationState.DRAFT:
        raise HTTPException(409, "Only DRAFT reservations can be confirmed")
    if reservation.number_of_people > room.capacity:
        raise HTTPException(422, f"Room capacity is {room.capacity} people")
    conflict = db.scalar(select(Reservation.id).where(
        Reservation.room_id == room.id,
        Reservation.id != reservation.id,
        Reservation.state == ReservationState.CONFIRMED,
        Reservation.start_time < reservation.end_time,
        Reservation.end_time > reservation.start_time,
    ).limit(1))
    if conflict is not None:
        raise HTTPException(409, "Another confirmed reservation overlaps this room and time")
    reservation.state = ReservationState.CONFIRMED
    return save(db, reservation)


@app.post("/reservations/{reservation_id}/cancel", response_model=ReservationRead)
@app.patch("/reservations/{reservation_id}/cancel", response_model=ReservationRead, include_in_schema=False)
def cancel_reservation(reservation_id: int, db: DB):
    reservation, _ = lock_reservation_room(db, reservation_id)
    if reservation.state == ReservationState.CANCELLED:
        raise HTTPException(409, "Reservation is already cancelled")
    reservation.state = ReservationState.CANCELLED
    return save(db, reservation)
