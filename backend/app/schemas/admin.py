from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminStats(BaseModel):
    workers_count: int
    employers_count: int
    jobs_count: int
    pending_verifications: int


class AdminAnalytics(BaseModel):
    workers_count: int
    employers_count: int
    jobs_count: int
    pending_verifications: int
    applications_by_status: dict[str, int] = Field(default_factory=dict)
    jobs_by_status: dict[str, int] = Field(default_factory=dict)


class PendingEmployerRead(BaseModel):
    id: UUID
    company_name: str
    contact_phone: str | None = None
    contact_person: str | None = None
    telegram_id: int
    username: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PendingWorkerRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    age: int
    metro_station_name: str | None = None
    categories: list[str] = Field(default_factory=list)
    telegram_id: int
    username: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
