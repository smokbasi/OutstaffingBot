from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.db.models import JobRequestStatus, RequiredGender

# NUMERIC(10, 2) in PostgreSQL: max absolute value < 10^8
MAX_HOURLY_RATE = Decimal("99999999.99")


class ShiftSlotCreate(BaseModel):
    shift_date: date
    start_time: time
    end_time: time
    slots_total: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def validate_times(self) -> "ShiftSlotCreate":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class ShiftSlotRead(BaseModel):
    id: UUID
    shift_date: date
    start_time: time
    end_time: time
    slots_total: int
    slots_filled: int

    model_config = {"from_attributes": True}


class JobRequestCreate(BaseModel):
    category_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    metro_station_id: int
    address: str | None = Field(default=None, max_length=300)
    hourly_rate: Decimal = Field(ge=0, le=MAX_HOURLY_RATE)
    workers_needed: int = Field(ge=1, le=100)
    min_experience_months: int | None = Field(default=None, ge=0, le=600)
    required_gender: RequiredGender | None = None
    min_age: int | None = Field(default=None, ge=16, le=70)
    max_age: int | None = Field(default=None, ge=16, le=70)
    dress_code: str | None = Field(default=None, max_length=200)
    contact_info: str | None = None
    post_to_groups: bool = False
    notify_matching_workers: bool = True
    shift_slots: list[ShiftSlotCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_age_range(self) -> "JobRequestCreate":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age must be less than or equal to max_age")
        return self


class JobRequestRead(BaseModel):
    id: UUID
    category_id: int
    category_name: str | None = None
    title: str
    description: str
    metro_station_id: int
    metro_station_name: str | None = None
    address: str | None = None
    hourly_rate: Decimal
    workers_needed: int
    min_experience_months: int | None = None
    required_gender: RequiredGender | None = None
    min_age: int | None = None
    max_age: int | None = None
    dress_code: str | None = None
    contact_info: str | None = None
    status: JobRequestStatus
    post_to_groups: bool
    notify_matching_workers: bool
    shift_slots: list[ShiftSlotRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobRequestUpdate(BaseModel):
    status: JobRequestStatus | None = None
