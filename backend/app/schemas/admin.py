from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminStats(BaseModel):
    workers_count: int
    employers_count: int
    jobs_count: int
    pending_verifications: int


class AdminAnalytics(AdminStats):
    applications_by_status: dict[str, int]
    jobs_by_status: dict[str, int]


class PendingEmployerRead(BaseModel):
    id: UUID
    company_name: str
    contact_phone: str | None
    contact_person: str | None
    telegram_id: int
    username: str | None
    created_at: datetime


class AdminAuditEntryRead(BaseModel):
    id: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str
    metadata: dict | None
    created_at: str
