"""Application complaints: create, permissions, deduplication, resolve/dismiss (Phase 9.9.2)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Application,
    ApplicationComplaint,
    ApplicationStatus,
    ComplaintReporterRole,
    ComplaintStatus,
    ComplaintViolationType,
    Employer,
    JobRequest,
    User,
    Worker,
)
from app.schemas.complaint import (
    ComplaintRead,
    EmployerComplaintApplicationRead,
    EmployerComplaintApplicationsResponse,
    EmployerComplaintJobRead,
    EmployerComplaintJobsResponse,
    WorkerComplaintContextResponse,
    WorkerEligibleApplicationRead,
)
from app.services import user_block_service

WORKER_DESCRIPTION_MIN_LENGTH = 20
DESCRIPTION_MAX_LENGTH = 2000


class ComplaintError(Exception):
    """Base error for complaint operations."""


class ComplaintNotFoundError(ComplaintError):
    pass


class ComplaintForbiddenError(ComplaintError):
    pass


class ComplaintDuplicateError(ComplaintError):
    pass


class ComplaintValidationError(ComplaintError):
    pass


class ComplaintNotEligibleError(ComplaintError):
    pass


class ComplaintStatusChangeError(ComplaintError):
    pass


def _normalize_description(description: str | None) -> str | None:
    if description is None:
        return None
    stripped = description.strip()
    return stripped or None


def _validate_worker_description(description: str | None) -> str:
    normalized = _normalize_description(description)
    if normalized is None or len(normalized) < WORKER_DESCRIPTION_MIN_LENGTH:
        raise ComplaintValidationError(
            f"Описание должно содержать не менее {WORKER_DESCRIPTION_MIN_LENGTH} символов."
        )
    if len(normalized) > DESCRIPTION_MAX_LENGTH:
        raise ComplaintValidationError(
            f"Описание не должно превышать {DESCRIPTION_MAX_LENGTH} символов."
        )
    return normalized


def _validate_employer_description(description: str | None) -> str | None:
    normalized = _normalize_description(description)
    if normalized is not None and len(normalized) > DESCRIPTION_MAX_LENGTH:
        raise ComplaintValidationError(
            f"Описание не должно превышать {DESCRIPTION_MAX_LENGTH} символов."
        )
    return normalized


def _ensure_application_accepted(application: Application) -> None:
    if application.status != ApplicationStatus.accepted:
        raise ComplaintNotEligibleError("Жалобу можно подать только по принятому отклику.")


async def _load_application(session: AsyncSession, application_id: UUID) -> Application | None:
    return await session.scalar(
        select(Application)
        .options(
            selectinload(Application.worker).selectinload(Worker.user),
            selectinload(Application.job_request).selectinload(JobRequest.employer).selectinload(
                Employer.user
            ),
            selectinload(Application.shift_slot),
        )
        .where(Application.id == application_id)
    )


async def _find_open_duplicate(
    session: AsyncSession,
    *,
    application_id: UUID,
    reporter_user_id: UUID,
    violation_type: ComplaintViolationType,
) -> ApplicationComplaint | None:
    return await session.scalar(
        select(ApplicationComplaint).where(
            ApplicationComplaint.application_id == application_id,
            ApplicationComplaint.reporter_user_id == reporter_user_id,
            ApplicationComplaint.violation_type == violation_type,
            ApplicationComplaint.status == ComplaintStatus.open,
        )
    )


async def _get_complaint(session: AsyncSession, complaint_id: UUID) -> ApplicationComplaint | None:
    return await session.get(ApplicationComplaint, complaint_id)


def _build_complaint(
    *,
    application: Application,
    reporter_user_id: UUID,
    reporter_role: ComplaintReporterRole,
    target_user_id: UUID,
    violation_type: ComplaintViolationType,
    description: str | None,
) -> ApplicationComplaint:
    return ApplicationComplaint(
        application_id=application.id,
        job_request_id=application.job_request_id,
        shift_slot_id=application.shift_slot_id,
        reporter_user_id=reporter_user_id,
        reporter_role=reporter_role,
        target_user_id=target_user_id,
        violation_type=violation_type,
        description=description,
        status=ComplaintStatus.open,
    )


def _complaint_to_read(complaint: ApplicationComplaint) -> ComplaintRead:
    created_at = complaint.created_at
    if created_at is None:
        created_at = datetime.now(UTC)
    return ComplaintRead(
        id=complaint.id,
        application_id=complaint.application_id,
        job_request_id=complaint.job_request_id,
        shift_slot_id=complaint.shift_slot_id,
        violation_type=complaint.violation_type,
        description=complaint.description,
        status=complaint.status,
        created_at=created_at,
    )


def _eligible_application_to_worker_read(application: Application) -> WorkerEligibleApplicationRead:
    job = application.job_request
    employer = job.employer if job is not None else None
    slot = application.shift_slot
    return WorkerEligibleApplicationRead(
        id=application.id,
        job_request_id=application.job_request_id,
        shift_slot_id=application.shift_slot_id,
        status=application.status,
        job_title=job.title if job is not None else "",
        company_name=employer.company_name if employer is not None else "",
        shift_date=slot.shift_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
    )


def _application_to_employer_complaint_read(application: Application) -> EmployerComplaintApplicationRead:
    job = application.job_request
    slot = application.shift_slot
    worker = application.worker
    return EmployerComplaintApplicationRead(
        id=application.id,
        job_request_id=application.job_request_id,
        shift_slot_id=application.shift_slot_id,
        status=application.status,
        job_title=job.title if job is not None else "",
        shift_date=slot.shift_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        worker_first_name=worker.first_name if worker is not None else None,
        worker_last_name=worker.last_name if worker is not None else None,
    )


async def get_worker_complaint_context(
    session: AsyncSession,
    worker: Worker,
) -> WorkerComplaintContextResponse:
    result = await session.scalars(
        select(Application)
        .options(
            selectinload(Application.shift_slot),
            selectinload(Application.job_request).selectinload(JobRequest.employer),
        )
        .where(
            Application.worker_id == worker.id,
            Application.status == ApplicationStatus.accepted,
        )
        .order_by(Application.applied_at.desc())
    )
    applications = [_eligible_application_to_worker_read(app) for app in result.all()]
    return WorkerComplaintContextResponse(applications=applications)


async def list_employer_complaint_jobs(
    session: AsyncSession,
    employer: Employer,
) -> EmployerComplaintJobsResponse:
    stmt = (
        select(
            JobRequest,
            func.count(Application.id).label("applications_count"),
        )
        .outerjoin(
            Application,
            (Application.job_request_id == JobRequest.id)
            & (Application.status == ApplicationStatus.accepted),
        )
        .where(JobRequest.employer_id == employer.id)
        .group_by(JobRequest.id)
        .having(func.count(Application.id) > 0)
        .order_by(JobRequest.created_at.desc())
    )
    rows = await session.execute(stmt)
    items = [
        EmployerComplaintJobRead(
            id=job.id,
            title=job.title,
            status=job.status,
            applications_count=applications_count,
        )
        for job, applications_count in rows.all()
    ]
    return EmployerComplaintJobsResponse(items=items)


async def list_employer_complaint_applications(
    session: AsyncSession,
    employer: Employer,
    job_id: UUID,
) -> EmployerComplaintApplicationsResponse:
    job = await session.scalar(
        select(JobRequest).where(
            JobRequest.id == job_id,
            JobRequest.employer_id == employer.id,
        )
    )
    if job is None:
        raise ComplaintNotFoundError("Заявка не найдена.")

    result = await session.scalars(
        select(Application)
        .options(
            selectinload(Application.shift_slot),
            selectinload(Application.job_request),
            selectinload(Application.worker),
        )
        .where(
            Application.job_request_id == job_id,
            Application.status == ApplicationStatus.accepted,
        )
        .order_by(Application.applied_at.desc())
    )
    items = [_application_to_employer_complaint_read(app) for app in result.all()]
    return EmployerComplaintApplicationsResponse(items=items, total=len(items))


async def create_worker_complaint(
    session: AsyncSession,
    worker: Worker,
    *,
    application_id: UUID,
    violation_type: ComplaintViolationType,
    description: str,
) -> ComplaintRead:
    user = getattr(worker, "user", None)
    if user is None and worker.user_id is not None:
        user = await session.get(User, worker.user_id)
    if user is None:
        raise ComplaintForbiddenError("Пользователь не найден.")
    user_block_service.ensure_not_blocked(user)

    application = await _load_application(session, application_id)
    if application is None or application.worker_id != worker.id:
        raise ComplaintNotFoundError("Отклик не найден.")

    _ensure_application_accepted(application)
    validated_description = _validate_worker_description(description)

    duplicate = await _find_open_duplicate(
        session,
        application_id=application.id,
        reporter_user_id=user.id,
        violation_type=violation_type,
    )
    if duplicate is not None:
        raise ComplaintDuplicateError("Открытая жалоба с таким типом уже существует.")

    job = application.job_request
    employer = job.employer if job is not None else None
    target_user = employer.user if employer is not None else None
    if target_user is None:
        raise ComplaintNotFoundError("Отклик не найден.")

    complaint = _build_complaint(
        application=application,
        reporter_user_id=user.id,
        reporter_role=ComplaintReporterRole.worker,
        target_user_id=target_user.id,
        violation_type=violation_type,
        description=validated_description,
    )
    session.add(complaint)
    await session.flush()
    return _complaint_to_read(complaint)


async def create_employer_complaint(
    session: AsyncSession,
    employer: Employer,
    *,
    application_id: UUID,
    violation_type: ComplaintViolationType,
    description: str | None = None,
) -> ComplaintRead:
    user = getattr(employer, "user", None)
    if user is None and employer.user_id is not None:
        user = await session.get(User, employer.user_id)
    if user is None:
        raise ComplaintForbiddenError("Пользователь не найден.")
    user_block_service.ensure_not_blocked(user)

    application = await _load_application(session, application_id)
    if application is None:
        raise ComplaintNotFoundError("Отклик не найден.")

    job = application.job_request
    if job is None or job.employer_id != employer.id:
        raise ComplaintNotFoundError("Отклик не найден.")

    _ensure_application_accepted(application)
    validated_description = _validate_employer_description(description)

    duplicate = await _find_open_duplicate(
        session,
        application_id=application.id,
        reporter_user_id=user.id,
        violation_type=violation_type,
    )
    if duplicate is not None:
        raise ComplaintDuplicateError("Открытая жалоба с таким типом уже существует.")

    worker = application.worker
    target_user = worker.user if worker is not None else None
    if target_user is None:
        raise ComplaintNotFoundError("Отклик не найден.")

    complaint = _build_complaint(
        application=application,
        reporter_user_id=user.id,
        reporter_role=ComplaintReporterRole.employer,
        target_user_id=target_user.id,
        violation_type=violation_type,
        description=validated_description,
    )
    session.add(complaint)
    await session.flush()
    return _complaint_to_read(complaint)


def _date_range_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _date_range_end(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _admin_complaint_list_options():
    return (
        selectinload(ApplicationComplaint.job_request).selectinload(JobRequest.employer),
    )


def _admin_complaint_detail_options():
    return (
        selectinload(ApplicationComplaint.reporter_user),
        selectinload(ApplicationComplaint.target_user),
        selectinload(ApplicationComplaint.job_request).selectinload(JobRequest.employer),
        selectinload(ApplicationComplaint.application).selectinload(Application.shift_slot),
        selectinload(ApplicationComplaint.shift_slot),
    )


async def list_admin_complaints(
    session: AsyncSession,
    *,
    violation_type: ComplaintViolationType | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    company_q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ApplicationComplaint], int]:
    filters: list = []
    if violation_type is not None:
        filters.append(ApplicationComplaint.violation_type == violation_type)
    if from_date is not None:
        filters.append(ApplicationComplaint.created_at >= _date_range_start(from_date))
    if to_date is not None:
        filters.append(ApplicationComplaint.created_at <= _date_range_end(to_date))

    base = (
        select(ApplicationComplaint)
        .join(JobRequest, ApplicationComplaint.job_request_id == JobRequest.id)
        .join(Employer, JobRequest.employer_id == Employer.id)
    )
    if company_q is not None:
        normalized_q = company_q.strip()
        if normalized_q:
            filters.append(Employer.company_name.ilike(f"%{normalized_q}%"))

    if filters:
        base = base.where(*filters)

    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await session.scalars(
        base.options(*_admin_complaint_list_options())
        .order_by(ApplicationComplaint.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.all()), total


async def get_admin_complaint_detail(
    session: AsyncSession,
    complaint_id: UUID,
) -> ApplicationComplaint | None:
    return await session.scalar(
        select(ApplicationComplaint)
        .options(*_admin_complaint_detail_options())
        .where(ApplicationComplaint.id == complaint_id)
    )


async def resolve_complaint(
    session: AsyncSession,
    complaint_id: UUID,
    *,
    admin_telegram_id: int,
    admin_notes: str | None = None,
) -> ApplicationComplaint:
    complaint = await _get_complaint(session, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Жалоба не найдена.")
    if complaint.status in (ComplaintStatus.resolved, ComplaintStatus.dismissed):
        raise ComplaintStatusChangeError("Жалоба уже закрыта.")

    complaint.status = ComplaintStatus.resolved
    complaint.admin_notes = _normalize_description(admin_notes)
    complaint.resolved_at = datetime.now(UTC)
    complaint.resolved_by_telegram_id = admin_telegram_id
    await session.flush()
    return complaint


async def dismiss_complaint(
    session: AsyncSession,
    complaint_id: UUID,
    *,
    admin_telegram_id: int,
    admin_notes: str | None = None,
) -> ApplicationComplaint:
    complaint = await _get_complaint(session, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Жалоба не найдена.")
    if complaint.status in (ComplaintStatus.resolved, ComplaintStatus.dismissed):
        raise ComplaintStatusChangeError("Жалоба уже закрыта.")

    complaint.status = ComplaintStatus.dismissed
    complaint.admin_notes = _normalize_description(admin_notes)
    complaint.resolved_at = datetime.now(UTC)
    complaint.resolved_by_telegram_id = admin_telegram_id
    await session.flush()
    return complaint
