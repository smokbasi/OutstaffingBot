from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import ApplicationStatus


class ApplicationCreate(BaseModel):
    shift_slot_id: UUID
    cancel_conflicting_id: UUID | None = None


class ConflictingShiftInfo(BaseModel):
    application_id: UUID
    shift_date: date
    start_time: time
    end_time: time
    job_title: str


class ApplicationRead(BaseModel):
    id: UUID
    job_request_id: UUID
    shift_slot_id: UUID
    status: ApplicationStatus
    applied_at: datetime
    cancelled_at: datetime | None = None
    job_title: str
    category_name: str | None = None
    metro_station_name: str | None = None
    hourly_rate: str
    shift_date: date
    start_time: time
    end_time: time


class ApplicationListResponse(BaseModel):
    items: list[ApplicationRead]
    total: int


class EmployerApplicationRead(BaseModel):
    id: UUID
    job_request_id: UUID
    shift_slot_id: UUID
    status: ApplicationStatus
    applied_at: datetime
    shift_date: date
    start_time: time
    end_time: time
    worker_id: UUID
    worker_first_name: str
    worker_last_name: str
    worker_age: int
    worker_experience_months: int | None = None


class EmployerApplicationListResponse(BaseModel):
    items: list[EmployerApplicationRead]
    total: int


class EmployerApplicationUpdate(BaseModel):
    status: Literal[ApplicationStatus.accepted, ApplicationStatus.rejected]


class ShiftConflictResponse(BaseModel):
    detail: str
    conflicting: ConflictingShiftInfo


APPLICATION_STATUS_LABELS: dict[ApplicationStatus, str] = {
    ApplicationStatus.pending: "На рассмотрении",
    ApplicationStatus.accepted: "Принят",
    ApplicationStatus.rejected: "Отклонён",
    ApplicationStatus.cancelled_by_worker: "Отменён вами",
    ApplicationStatus.cancelled_by_employer: "Отменён работодателем",
}


def format_application_status(status: ApplicationStatus) -> str:
    return APPLICATION_STATUS_LABELS.get(status, status.value)
