"""Unit tests for complaint_service (Phase 9.9.2): IDOR, dedup, validation."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.models import (
    ApplicationStatus,
    ComplaintReporterRole,
    ComplaintStatus,
    ComplaintViolationType,
)
from app.services import complaint_service, user_block_service


def _make_user(*, is_blocked: bool = False):
    user_id = uuid4()
    user = type("User", (), {})()
    user.id = user_id
    user.telegram_id = 1001
    user.is_blocked = is_blocked
    return user


def _make_worker(*, user: object | None = None):
    worker = type("Worker", (), {})()
    worker.id = uuid4()
    worker.user = user or _make_user()
    worker.user_id = worker.user.id
    return worker


def _make_employer(*, user: object | None = None):
    employer = type("Employer", (), {})()
    employer.id = uuid4()
    employer.user = user or _make_user()
    employer.user_id = employer.user.id
    return employer


def _make_application(
    *,
    worker: object,
    employer: object,
    status: ApplicationStatus = ApplicationStatus.accepted,
):
    application = type("Application", (), {})()
    application.id = uuid4()
    application.worker_id = worker.id
    application.worker = worker
    application.job_request_id = uuid4()
    application.shift_slot_id = uuid4()
    application.status = status

    job = type("JobRequest", (), {})()
    job.id = application.job_request_id
    job.employer_id = employer.id
    job.employer = employer
    application.job_request = job

    slot = type("ShiftSlot", (), {})()
    slot.id = application.shift_slot_id
    application.shift_slot = slot
    return application


class FakeSession:
    def __init__(
        self,
        *,
        application: object | None = None,
        duplicate: object | None = None,
        complaint: object | None = None,
    ) -> None:
        self.application = application
        self.duplicate = duplicate
        self.complaint = complaint
        self.added: list[object] = []

    async def scalar(self, stmt):
        compiled = str(stmt)
        if "application_complaints" in compiled and "status" in compiled:
            return self.duplicate
        if "applications" in compiled:
            return self.application
        return None

    async def get(self, model, obj_id):
        if self.complaint is not None and getattr(self.complaint, "id", None) == obj_id:
            return self.complaint
        return None

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_create_worker_complaint_success() -> None:
    worker = _make_worker()
    employer = _make_employer()
    application = _make_application(worker=worker, employer=employer)
    session = FakeSession(application=application)

    complaint = await complaint_service.create_worker_complaint(
        session,
        worker,
        application_id=application.id,
        violation_type=ComplaintViolationType.late,
        description="Работодатель опоздал более чем на час.",
    )

    assert len(session.added) == 1
    assert complaint.reporter_role == ComplaintReporterRole.worker
    assert complaint.target_user_id == employer.user.id
    assert complaint.violation_type == ComplaintViolationType.late
    assert complaint.status == ComplaintStatus.open


@pytest.mark.asyncio
async def test_create_employer_complaint_without_description() -> None:
    worker = _make_worker()
    employer = _make_employer()
    application = _make_application(worker=worker, employer=employer)
    session = FakeSession(application=application)

    complaint = await complaint_service.create_employer_complaint(
        session,
        employer,
        application_id=application.id,
        violation_type=ComplaintViolationType.no_show,
    )

    assert complaint.description is None
    assert complaint.reporter_role == ComplaintReporterRole.employer
    assert complaint.target_user_id == worker.user.id


@pytest.mark.asyncio
async def test_worker_idor_other_workers_application_raises_not_found() -> None:
    owner = _make_worker()
    other = _make_worker()
    employer = _make_employer()
    application = _make_application(worker=owner, employer=employer)
    session = FakeSession(application=application)

    with pytest.raises(complaint_service.ComplaintNotFoundError):
        await complaint_service.create_worker_complaint(
            session,
            other,
            application_id=application.id,
            violation_type=ComplaintViolationType.no_payment,
            description="Оплата за смену так и не поступила.",
        )


@pytest.mark.asyncio
async def test_employer_idor_other_employers_job_raises_not_found() -> None:
    worker = _make_worker()
    owner = _make_employer()
    other = _make_employer()
    application = _make_application(worker=worker, employer=owner)
    session = FakeSession(application=application)

    with pytest.raises(complaint_service.ComplaintNotFoundError):
        await complaint_service.create_employer_complaint(
            session,
            other,
            application_id=application.id,
            violation_type=ComplaintViolationType.no_show,
        )


@pytest.mark.asyncio
async def test_blocked_worker_raises_forbidden() -> None:
    worker = _make_worker(user=_make_user(is_blocked=True))
    employer = _make_employer()
    application = _make_application(worker=worker, employer=employer)
    session = FakeSession(application=application)

    with pytest.raises(user_block_service.UserBlockedError):
        await complaint_service.create_worker_complaint(
            session,
            worker,
            application_id=application.id,
            violation_type=ComplaintViolationType.late,
            description="Работодатель опоздал более чем на час.",
        )


@pytest.mark.asyncio
async def test_blocked_employer_raises_forbidden() -> None:
    worker = _make_worker()
    employer = _make_employer(user=_make_user(is_blocked=True))
    application = _make_application(worker=worker, employer=employer)
    session = FakeSession(application=application)

    with pytest.raises(user_block_service.UserBlockedError):
        await complaint_service.create_employer_complaint(
            session,
            employer,
            application_id=application.id,
            violation_type=ComplaintViolationType.no_show,
        )


@pytest.mark.asyncio
async def test_worker_description_too_short_raises_validation() -> None:
    worker = _make_worker()
    employer = _make_employer()
    application = _make_application(worker=worker, employer=employer)
    session = FakeSession(application=application)

    with pytest.raises(complaint_service.ComplaintValidationError):
        await complaint_service.create_worker_complaint(
            session,
            worker,
            application_id=application.id,
            violation_type=ComplaintViolationType.no_work,
            description="коротко",
        )


@pytest.mark.asyncio
async def test_pending_application_raises_not_eligible() -> None:
    worker = _make_worker()
    employer = _make_employer()
    application = _make_application(
        worker=worker,
        employer=employer,
        status=ApplicationStatus.pending,
    )
    session = FakeSession(application=application)

    with pytest.raises(complaint_service.ComplaintNotEligibleError):
        await complaint_service.create_worker_complaint(
            session,
            worker,
            application_id=application.id,
            violation_type=ComplaintViolationType.late,
            description="Работодатель опоздал более чем на час.",
        )


@pytest.mark.asyncio
async def test_duplicate_open_complaint_raises_conflict() -> None:
    worker = _make_worker()
    employer = _make_employer()
    application = _make_application(worker=worker, employer=employer)
    existing = type("ApplicationComplaint", (), {})()
    existing.id = uuid4()
    session = FakeSession(application=application, duplicate=existing)

    with pytest.raises(complaint_service.ComplaintDuplicateError):
        await complaint_service.create_worker_complaint(
            session,
            worker,
            application_id=application.id,
            violation_type=ComplaintViolationType.late,
            description="Работодатель опоздал более чем на час.",
        )


@pytest.mark.asyncio
async def test_worker_complaint_accepts_stop_words_without_moderation() -> None:
    worker = _make_worker()
    employer = _make_employer()
    application = _make_application(worker=worker, employer=employer)
    session = FakeSession(application=application)
    profane_description = "Это описание содержит заведомо запрещённое слово хуйня."

    complaint = await complaint_service.create_worker_complaint(
        session,
        worker,
        application_id=application.id,
        violation_type=ComplaintViolationType.no_payment,
        description=profane_description,
    )

    assert complaint.description == profane_description


@pytest.mark.asyncio
async def test_resolve_complaint_sets_status_and_admin_notes() -> None:
    complaint = type("ApplicationComplaint", (), {})()
    complaint.id = uuid4()
    complaint.status = ComplaintStatus.open
    complaint.admin_notes = None
    complaint.resolved_at = None
    complaint.resolved_by_telegram_id = None
    session = FakeSession(complaint=complaint)

    result = await complaint_service.resolve_complaint(
        session,
        complaint.id,
        admin_telegram_id=999,
        admin_notes="  Подтверждено по переписке  ",
    )

    assert result.status == ComplaintStatus.resolved
    assert result.admin_notes == "Подтверждено по переписке"
    assert result.resolved_by_telegram_id == 999
    assert result.resolved_at is not None


@pytest.mark.asyncio
async def test_dismiss_complaint_sets_status() -> None:
    complaint = type("ApplicationComplaint", (), {})()
    complaint.id = uuid4()
    complaint.status = ComplaintStatus.under_review
    complaint.admin_notes = None
    complaint.resolved_at = None
    complaint.resolved_by_telegram_id = None
    session = FakeSession(complaint=complaint)

    result = await complaint_service.dismiss_complaint(
        session,
        complaint.id,
        admin_telegram_id=999,
        admin_notes=None,
    )

    assert result.status == ComplaintStatus.dismissed
    assert result.admin_notes is None


@pytest.mark.asyncio
async def test_resolve_already_closed_complaint_raises() -> None:
    complaint = type("ApplicationComplaint", (), {})()
    complaint.id = uuid4()
    complaint.status = ComplaintStatus.resolved
    session = FakeSession(complaint=complaint)

    with pytest.raises(complaint_service.ComplaintStatusChangeError):
        await complaint_service.dismiss_complaint(
            session,
            complaint.id,
            admin_telegram_id=999,
        )
