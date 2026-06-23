from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import (
    ApplicationStatus,
    ComplaintStatus,
    ComplaintViolationType,
    JobRequestStatus,
)


COMPLAINT_VIOLATION_TYPE_LABELS: dict[ComplaintViolationType, str] = {
    ComplaintViolationType.late: "Опоздание",
    ComplaintViolationType.no_show: "Невыход на смену",
    ComplaintViolationType.no_payment: "Отсутствие оплаты",
    ComplaintViolationType.no_work: "Отсутствие работы",
}


class WorkerEligibleApplicationRead(BaseModel):
    id: UUID
    job_request_id: UUID
    shift_slot_id: UUID
    status: ApplicationStatus
    job_title: str
    company_name: str
    shift_date: date
    start_time: time
    end_time: time


class WorkerComplaintContextResponse(BaseModel):
    applications: list[WorkerEligibleApplicationRead]


class WorkerComplaintCreate(BaseModel):
    application_id: UUID
    violation_type: ComplaintViolationType
    description: str = Field(min_length=1)


class EmployerComplaintCreate(BaseModel):
    application_id: UUID
    violation_type: ComplaintViolationType
    description: str | None = None


class ComplaintRead(BaseModel):
    id: UUID
    application_id: UUID
    job_request_id: UUID
    shift_slot_id: UUID
    violation_type: ComplaintViolationType
    description: str | None
    status: ComplaintStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployerComplaintJobRead(BaseModel):
    id: UUID
    title: str
    status: JobRequestStatus
    applications_count: int


class EmployerComplaintJobsResponse(BaseModel):
    items: list[EmployerComplaintJobRead]


class EmployerComplaintApplicationRead(BaseModel):
    id: UUID
    job_request_id: UUID
    shift_slot_id: UUID
    status: ApplicationStatus
    job_title: str
    shift_date: date
    start_time: time
    end_time: time
    worker_first_name: str | None = None
    worker_last_name: str | None = None


class EmployerComplaintApplicationsResponse(BaseModel):
    items: list[EmployerComplaintApplicationRead]
    total: int
