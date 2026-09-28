from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


def utc_now():
    """Server clock; tests replace this function for exact deadline boundaries."""
    return datetime.now(timezone.utc)


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ReservationState(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="user", foreign_keys="Reservation.user_id"
    )


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_room_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    approver_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="room"
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "end_time > start_time",
            name="ck_reservation_time_order",
        ),
        CheckConstraint(
            "number_of_people > 0",
            name="ck_reservation_people_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    number_of_people: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[ReservationState] = mapped_column(
        SQLEnum(ReservationState, name="reservation_state"),
        default=ReservationState.DRAFT,
        nullable=False,
    )

    approval_decision: Mapped[ApprovalStatus] = mapped_column(
        SQLEnum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.NOT_REQUIRED, server_default="NOT_REQUIRED", nullable=False,
    )
    approval_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def effective_approval_status(self, now: datetime) -> ApprovalStatus:
        if (self.state == ReservationState.DRAFT
                and self.approval_decision in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED)
                and self.approval_deadline is not None and now >= self.approval_deadline):
            return ApprovalStatus.EXPIRED
        return self.approval_decision

    @property
    def approval_status(self) -> ApprovalStatus:
        return self.effective_approval_status(utc_now())

    user: Mapped["User"] = relationship(back_populates="reservations", foreign_keys=[user_id])
    room: Mapped["Room"] = relationship(back_populates="reservations")

    @property
    def room_name(self) -> str:
        """Expose the related room code in API responses without duplicating it."""
        return self.room.name
