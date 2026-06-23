"""Application complaints: create, permissions, deduplication, resolve/dismiss (Phase 9.9.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
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


async def create_worker_complaint(
    session: AsyncSession,
    worker: Worker,
    *,
    application_id: UUID,
    violation_type: ComplaintViolationType,
    description: str,
) -> ApplicationComplaint:
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
    return complaint


async def create_employer_complaint(
    session: AsyncSession,
    employer: Employer,
    *,
    application_id: UUID,
    violation_type: ComplaintViolationType,
    description: str | None = None,
) -> ApplicationComplaint:
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
    return complaint


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
