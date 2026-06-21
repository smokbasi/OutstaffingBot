from datetime import datetime, time, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Application,
    ApplicationStatus,
    JobRequest,
    JobRequestStatus,
    ShiftSlot,
    Worker,
)
from app.schemas.application import ApplicationListResponse, ApplicationRead
from app.services import matching_service


def shifts_overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return a_start < b_end and b_start < a_end


class ApplicationError(Exception):
    """Base error for application operations."""


class ShiftConflictError(ApplicationError):
    def __init__(self, conflicting_application: Application) -> None:
        self.conflicting_application = conflicting_application
        super().__init__("Shift conflict")


class SlotUnavailableError(ApplicationError):
    pass


class AlreadyAppliedError(ApplicationError):
    pass


class ApplicationNotFoundError(ApplicationError):
    pass


class ApplicationNotCancellableError(ApplicationError):
    pass


class CancelConflictMismatchError(ApplicationError):
    def __init__(self, expected_id: UUID) -> None:
        self.expected_id = expected_id
        super().__init__("Conflicting application id mismatch")


async def has_shift_conflict(
    session: AsyncSession,
    worker_id: UUID,
    new_slot: ShiftSlot,
) -> Application | None:
    stmt = (
        select(Application)
        .options(
            selectinload(Application.shift_slot),
            selectinload(Application.job_request),
        )
        .join(ShiftSlot, Application.shift_slot_id == ShiftSlot.id)
        .where(
            Application.worker_id == worker_id,
            Application.status.in_([ApplicationStatus.pending, ApplicationStatus.accepted]),
            ShiftSlot.shift_date == new_slot.shift_date,
            ShiftSlot.start_time < new_slot.end_time,
            new_slot.start_time < ShiftSlot.end_time,
        )
    )
    return await session.scalar(stmt)


async def _get_shift_slot(session: AsyncSession, shift_slot_id: UUID) -> ShiftSlot | None:
    return await session.scalar(
        select(ShiftSlot)
        .options(
            selectinload(ShiftSlot.job_request).selectinload(JobRequest.category),
            selectinload(ShiftSlot.job_request).selectinload(JobRequest.metro_station),
        )
        .where(ShiftSlot.id == shift_slot_id)
    )


async def _get_existing_application(
    session: AsyncSession,
    worker_id: UUID,
    shift_slot_id: UUID,
) -> Application | None:
    return await session.scalar(
        select(Application).where(
            Application.worker_id == worker_id,
            Application.shift_slot_id == shift_slot_id,
            Application.status.in_([ApplicationStatus.pending, ApplicationStatus.accepted]),
        )
    )


def _application_to_read(app: Application) -> ApplicationRead:
    slot = app.shift_slot
    job = app.job_request
    return ApplicationRead(
        id=app.id,
        job_request_id=app.job_request_id,
        shift_slot_id=app.shift_slot_id,
        status=app.status,
        applied_at=app.applied_at,
        cancelled_at=app.cancelled_at,
        job_title=job.title if job else "",
        category_name=job.category.name_ru if job and job.category else None,
        metro_station_name=job.metro_station.name if job and job.metro_station else None,
        hourly_rate=str(job.hourly_rate) if job else "0",
        shift_date=slot.shift_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
    )


async def apply_to_shift(
    session: AsyncSession,
    worker: Worker,
    shift_slot_id: UUID,
    *,
    cancel_conflicting_id: UUID | None = None,
) -> ApplicationRead:
    slot = await _get_shift_slot(session, shift_slot_id)
    if slot is None:
        raise ApplicationNotFoundError("Shift slot not found")

    job = slot.job_request
    if job is None or job.status != JobRequestStatus.active:
        raise SlotUnavailableError("Vacancy is not available")

    if slot.slots_filled >= slot.slots_total:
        raise SlotUnavailableError("No free slots on this shift")

    vacancy = await matching_service.get_vacancy_for_worker(session, worker, job.id)
    if vacancy is None:
        raise SlotUnavailableError("Vacancy does not match your profile")

    existing = await _get_existing_application(session, worker.id, shift_slot_id)
    if existing is not None:
        raise AlreadyAppliedError("You already applied to this shift")

    conflict = await has_shift_conflict(session, worker.id, slot)
    if conflict is not None:
        if cancel_conflicting_id is not None:
            if conflict.id != cancel_conflicting_id:
                raise CancelConflictMismatchError(expected_id=conflict.id)
            await cancel_application(session, worker, cancel_conflicting_id)
            conflict = await has_shift_conflict(session, worker.id, slot)
            if conflict is not None:
                raise ShiftConflictError(conflict)
        else:
            raise ShiftConflictError(conflict)

    application = Application(
        worker_id=worker.id,
        job_request_id=job.id,
        shift_slot_id=slot.id,
        status=ApplicationStatus.pending,
    )
    session.add(application)
    await session.flush()

    loaded = await session.scalar(
        select(Application)
        .options(
            selectinload(Application.shift_slot),
            selectinload(Application.job_request).selectinload(JobRequest.category),
            selectinload(Application.job_request).selectinload(JobRequest.metro_station),
        )
        .where(Application.id == application.id)
    )
    assert loaded is not None
    return _application_to_read(loaded)


async def cancel_application(
    session: AsyncSession,
    worker: Worker,
    application_id: UUID,
) -> ApplicationRead:
    app = await session.scalar(
        select(Application)
        .options(
            selectinload(Application.shift_slot),
            selectinload(Application.job_request).selectinload(JobRequest.category),
            selectinload(Application.job_request).selectinload(JobRequest.metro_station),
        )
        .where(Application.id == application_id, Application.worker_id == worker.id)
    )
    if app is None:
        raise ApplicationNotFoundError("Application not found")

    if app.status not in (ApplicationStatus.pending, ApplicationStatus.accepted):
        raise ApplicationNotCancellableError("Application cannot be cancelled")

    if app.status == ApplicationStatus.accepted:
        slot = app.shift_slot
        if slot is not None and slot.slots_filled > 0:
            slot.slots_filled -= 1

    app.status = ApplicationStatus.cancelled_by_worker
    app.cancelled_at = datetime.now(timezone.utc)
    await session.flush()
    return _application_to_read(app)


async def list_my_applications(
    session: AsyncSession,
    worker: Worker,
) -> ApplicationListResponse:
    result = await session.scalars(
        select(Application)
        .options(
            selectinload(Application.shift_slot),
            selectinload(Application.job_request).selectinload(JobRequest.category),
            selectinload(Application.job_request).selectinload(JobRequest.metro_station),
        )
        .where(
            Application.worker_id == worker.id,
            Application.status.in_([ApplicationStatus.pending, ApplicationStatus.accepted]),
        )
        .order_by(Application.applied_at.desc())
    )
    items = [_application_to_read(app) for app in result.all()]
    return ApplicationListResponse(items=items, total=len(items))
