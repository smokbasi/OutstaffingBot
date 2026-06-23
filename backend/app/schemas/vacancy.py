from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.job_request import ShiftSlotRead


class VacancyFilters(BaseModel):
    category_id: int | None = None
    metro_station_id: int | None = None
    min_hourly_rate: Decimal | None = Field(default=None, ge=0)
    city: str | None = None
    max_distance_km: int | None = Field(default=None, ge=0, le=100)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class VacancyListItem(BaseModel):
    id: UUID
    category_id: int
    category_name: str | None = None
    title: str
    metro_station_id: int
    metro_station_name: str | None = None
    hourly_rate: Decimal
    workers_needed: int
    next_shift_date: date | None = None
    next_shift_start: time | None = None
    next_shift_end: time | None = None
    available_slots: int = 0
    includes_lunch: bool = False


class VacancyListResponse(BaseModel):
    items: list[VacancyListItem]
    total: int
    page: int
    limit: int


class VacancyDetail(BaseModel):
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
    dress_code: str | None = None
    includes_lunch: bool = False
    shift_slots: list[ShiftSlotRead] = Field(default_factory=list)
    created_at: datetime
