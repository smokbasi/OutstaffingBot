from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import Gender


class WorkerExperienceRead(BaseModel):
    id: UUID
    category_id: int
    category_name: str
    role_title: str
    duration_months: int
    description: str | None = None

    model_config = {"from_attributes": True}


class WorkerProfileRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    age: int
    gender: Gender | None = None
    metro_station_id: int | None = None
    metro_station_name: str | None = None
    min_hourly_rate: Decimal | None = None
    phone: str | None = Field(default=None, max_length=20)
    verified: bool = False
    resume_completed: bool
    experiences: list[WorkerExperienceRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WorkerProfileUpdate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=16, le=70)
    gender: Gender | None = None
    metro_station_id: int | None = None
    min_hourly_rate: Decimal | None = Field(default=None, ge=0)
    phone: str | None = Field(default=None, max_length=20)


class WorkerExperienceCreate(BaseModel):
    category_id: int
    role_title: str = Field(min_length=1, max_length=200)
    duration_months: int = Field(ge=0, le=600)
    description: str | None = None
