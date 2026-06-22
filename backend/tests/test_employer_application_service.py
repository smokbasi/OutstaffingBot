from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest

from app.db.models import ApplicationStatus, JobRequestStatus
from app.services.application_service import (
    ApplicationNotFoundError,
    ApplicationNotPendingError,
    JobNotFoundForEmployerError,
    SlotFullError,
    update_application_by_employer,
)


class _Worker:
    def __init__(self) -> None:
        self.id = uuid4()
        self.first_name = "Пётр"
        self.last_name = "Иванов"
        self.age = 25
        self.experiences: list = []


class _Slot:
    def __init__(self, *, slots_total: int = 2, slots_filled: int = 0) -> None:
        self.id = uuid4()
        self.shift_date = date(2026, 6, 25)
        self.start_time = time(10, 0)
        self.end_time = time(22, 0)
        self.slots_total = slots_total
        self.slots_filled = slots_filled


class _Job:
    def __init__(self, employer_id) -> None:
        self.id = uuid4()
        self.employer_id = employer_id
        self.status = JobRequestStatus.active
        self.shift_slots: list = []


class _Application:
    def __init__(self, *, worker: _Worker, slot: _Slot, job: _Job) -> None:
        self.id = uuid4()
        self.worker_id = worker.id
        self.job_request_id = job.id
        self.shift_slot_id = slot.id
        self.status = ApplicationStatus.pending
        self.applied_at = datetime.now(timezone.utc)
        self.worker = worker
        self.shift_slot = slot
        self.job_request = job


@pytest.mark.asyncio
async def test_update_application_accept_increments_slots_filled() -> None:
    employer_id = uuid4()
    worker = _Worker()
    slot = _Slot(slots_total=2, slots_filled=0)
    job = _Job(employer_id)
    application = _Application(worker=worker, slot=slot, job=job)

    class DummySession:
        async def scalar(self, stmt):
            return application

        async def flush(self) -> None:
            return None

    result = await update_application_by_employer(
        DummySession(),
        employer_id,
        application.id,
        ApplicationStatus.accepted,
    )
    assert result.status == ApplicationStatus.accepted
    assert slot.slots_filled == 1


@pytest.mark.asyncio
async def test_update_application_reject_does_not_increment_slots() -> None:
    employer_id = uuid4()
    worker = _Worker()
    slot = _Slot()
    job = _Job(employer_id)
    application = _Application(worker=worker, slot=slot, job=job)

    class DummySession:
        async def scalar(self, stmt):
            return application

        async def flush(self) -> None:
            return None

    result = await update_application_by_employer(
        DummySession(),
        employer_id,
        application.id,
        ApplicationStatus.rejected,
    )
    assert result.status == ApplicationStatus.rejected
    assert slot.slots_filled == 0


@pytest.mark.asyncio
async def test_update_application_slot_full_raises() -> None:
    employer_id = uuid4()
    worker = _Worker()
    slot = _Slot(slots_total=1, slots_filled=1)
    job = _Job(employer_id)
    application = _Application(worker=worker, slot=slot, job=job)

    class DummySession:
        async def scalar(self, stmt):
            return application

    with pytest.raises(SlotFullError):
        await update_application_by_employer(
            DummySession(),
            employer_id,
            application.id,
            ApplicationStatus.accepted,
        )


@pytest.mark.asyncio
async def test_update_application_not_pending_raises() -> None:
    employer_id = uuid4()
    worker = _Worker()
    slot = _Slot()
    job = _Job(employer_id)
    application = _Application(worker=worker, slot=slot, job=job)
    application.status = ApplicationStatus.accepted

    class DummySession:
        async def scalar(self, stmt):
            return application

    with pytest.raises(ApplicationNotPendingError):
        await update_application_by_employer(
            DummySession(),
            employer_id,
            application.id,
            ApplicationStatus.rejected,
        )


@pytest.mark.asyncio
async def test_update_application_wrong_employer_raises() -> None:
    employer_id = uuid4()
    other_employer_id = uuid4()
    worker = _Worker()
    slot = _Slot()
    job = _Job(other_employer_id)
    application = _Application(worker=worker, slot=slot, job=job)

    class DummySession:
        async def scalar(self, stmt):
            return application

    with pytest.raises(ApplicationNotFoundError):
        await update_application_by_employer(
            DummySession(),
            employer_id,
            application.id,
            ApplicationStatus.accepted,
        )


@pytest.mark.asyncio
async def test_list_job_applications_job_not_found() -> None:
    from app.services.application_service import list_job_applications

    employer_id = uuid4()
    job_id = uuid4()

    class DummySession:
        async def scalar(self, stmt):
            return None

    with pytest.raises(JobNotFoundForEmployerError):
        await list_job_applications(DummySession(), employer_id, job_id)
