"""API validation and response contracts for the shared persistence models."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator,
)

from src.models import ApprovalStatus, ReservationState

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class UserCreate(BaseModel):
    name: Name
    email: ShortText


class UserRead(UserCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RoomCreate(BaseModel):
    name: Name
    location: ShortText
    capacity: int = Field(gt=0)
    requires_approval: bool = False
    approver_user_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_approver(self) -> Self:
        if self.requires_approval != (self.approver_user_id is not None):
            raise ValueError("Approval rooms require an approver; ordinary rooms must omit one")
        return self


class RoomRead(RoomCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ReservationCreate(BaseModel):
    user_id: int = Field(gt=0)
    room_id: int = Field(gt=0)
    start_time: AwareDatetime
    end_time: AwareDatetime
    number_of_people: int = Field(gt=0)
    purpose: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    @model_validator(mode="after")
    def check_time_order(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        return self


class ReservationRead(ReservationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    state: ReservationState
    room_name: str

    approval_decision: ApprovalStatus
    approval_status: ApprovalStatus
    approval_deadline: datetime | None
    decided_by: int | None
    decided_at: datetime | None


class ApprovalDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
