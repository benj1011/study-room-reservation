"""API validation and response contracts for the shared persistence models."""

from typing import Annotated, Self

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator,
)

from src.models import ReservationState

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
