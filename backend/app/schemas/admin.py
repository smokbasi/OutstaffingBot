from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminStats(BaseModel):
    workers_count: int
    employers_count: int
    jobs_count: int
    pending_verifications: int
    users_blocked: int = 0
    moderation_flagged_users: int = 0
    violations_total: int = 0


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


class ModerationQueueEntryRead(BaseModel):
    telegram_id: int
    username: str | None
    violation_count: int
    is_blocked: bool
    flagged_at: datetime


class ModerationViolationRead(BaseModel):
    id: UUID
    field: str
    category: str | None
    matched_term: str
    raw_snippet: str
    source: str
    created_at: datetime


class ModerationUserDetailRead(BaseModel):
    telegram_id: int
    username: str | None
    is_blocked: bool
    flagged_at: datetime | None
    violation_count: int
    violations: list[ModerationViolationRead]


class AdminAuditEntryRead(BaseModel):
    id: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str
    metadata: dict | None
    created_at: str
