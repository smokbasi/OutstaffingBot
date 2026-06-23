from datetime import UTC, date, datetime, time
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.db.models import (
    ComplaintReporterRole,
    ComplaintStatus,
    ComplaintViolationType,
)
from app.schemas.complaint import COMPLAINT_VIOLATION_TYPE_LABELS


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


class AdminComplaintListItem(BaseModel):
    id: UUID
    violation_type: ComplaintViolationType
    violation_type_label: str
    status: ComplaintStatus
    reporter_role: ComplaintReporterRole
    company_name: str
    job_title: str
    created_at: datetime


class AdminComplaintListResponse(BaseModel):
    items: list[AdminComplaintListItem]
    total: int
    limit: int
    offset: int


class AdminComplaintUserBrief(BaseModel):
    telegram_id: int
    username: str | None


class AdminComplaintDetail(BaseModel):
    id: UUID
    application_id: UUID
    job_request_id: UUID
    shift_slot_id: UUID
    violation_type: ComplaintViolationType
    violation_type_label: str
    description: str | None
    status: ComplaintStatus
    reporter_role: ComplaintReporterRole
    reporter: AdminComplaintUserBrief
    target: AdminComplaintUserBrief
    company_name: str
    job_title: str
    shift_date: date
    start_time: time
    end_time: time
    admin_notes: str | None
    resolved_at: datetime | None
    resolved_by_telegram_id: int | None
    created_at: datetime


class AdminComplaintPatch(BaseModel):
    status: ComplaintStatus
    admin_notes: str | None = None

    @field_validator("status")
    @classmethod
    def status_must_be_terminal(cls, value: ComplaintStatus) -> ComplaintStatus:
        if value not in (ComplaintStatus.resolved, ComplaintStatus.dismissed):
            raise ValueError("status must be resolved or dismissed")
        return value


def complaint_violation_label(violation_type: ComplaintViolationType) -> str:
    return COMPLAINT_VIOLATION_TYPE_LABELS.get(violation_type, violation_type.value)
