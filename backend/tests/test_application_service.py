from datetime import date, time
from uuid import uuid4

import pytest

from app.services.application_service import shifts_overlap


def test_shifts_overlap_true_when_ranges_intersect() -> None:
    assert shifts_overlap(time(10, 0), time(18, 0), time(14, 0), time(22, 0)) is True


def test_shifts_overlap_false_when_adjacent() -> None:
    assert shifts_overlap(time(10, 0), time(18, 0), time(18, 0), time(22, 0)) is False


def test_shifts_overlap_false_when_disjoint() -> None:
    assert shifts_overlap(time(8, 0), time(12, 0), time(14, 0), time(18, 0)) is False


def test_shifts_overlap_true_when_one_contains_other() -> None:
    assert shifts_overlap(time(9, 0), time(21, 0), time(10, 0), time(18, 0)) is True


def test_shifts_overlap_same_times() -> None:
    assert shifts_overlap(time(10, 0), time(18, 0), time(10, 0), time(18, 0)) is True


class _Slot:
    def __init__(
        self,
        *,
        shift_date: date = date(2026, 6, 19),
        start_time: time = time(10, 0),
        end_time: time = time(18, 0),
    ) -> None:
        self.shift_date = shift_date
        self.start_time = start_time
        self.end_time = end_time


class _Application:
    def __init__(self, slot: _Slot) -> None:
        self.id = uuid4()
        self.shift_slot = slot


@pytest.mark.asyncio
async def test_has_shift_conflict_returns_conflicting_application(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import application_service

    conflicting = _Application(_Slot())
    new_slot = _Slot(start_time=time(14, 0), end_time=time(22, 0))

    async def mock_scalar(stmt):
        return conflicting

    class DummySession:
        async def scalar(self, stmt):
            return await mock_scalar(stmt)

    result = await application_service.has_shift_conflict(DummySession(), uuid4(), new_slot)
    assert result is conflicting


@pytest.mark.asyncio
async def test_has_shift_conflict_returns_none_when_no_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import application_service

    new_slot = _Slot(start_time=time(18, 0), end_time=time(22, 0))

    class DummySession:
        async def scalar(self, stmt):
            return None

    result = await application_service.has_shift_conflict(DummySession(), uuid4(), new_slot)
    assert result is None


@pytest.mark.asyncio
async def test_apply_to_shift_reactivates_cancelled_application(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime, timezone
    from decimal import Decimal

    from app.db.models import ApplicationStatus, JobRequestStatus, VerificationStatus
    from app.services import application_service

    worker_id = uuid4()
    slot_id = uuid4()
    job_id = uuid4()

    class Worker:
        id = worker_id
        verification_status = VerificationStatus.verified

    class Category:
        name_ru = "Официант"

    class Metro:
        name = "Автово"

    class Job:
        id = job_id
        title = "Официант"
        status = JobRequestStatus.active
        category = Category()
        metro_station = Metro()
        hourly_rate = Decimal("400")

    class Slot:
        id = slot_id
        shift_date = date(2026, 6, 25)
        start_time = time(10, 0)
        end_time = time(22, 0)
        slots_filled = 0
        slots_total = 2
        job_request = Job()

    slot = Slot()
    job = Job()

    class ExistingApplication:
        id = uuid4()
        status = ApplicationStatus.cancelled_by_worker
        cancelled_at = datetime.now(timezone.utc)
        applied_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

    existing = ExistingApplication()
    existing.worker_id = worker_id
    existing.job_request_id = job_id
    existing.shift_slot_id = slot_id
    existing.shift_slot = slot
    existing.job_request = job
    scalar_calls: list[object] = []

    async def mock_get_shift_slot(session, shift_slot_id):
        assert shift_slot_id == slot_id
        return slot

    async def mock_get_vacancy_for_worker(session, worker, job_request_id):
        return object()

    async def mock_has_shift_conflict(session, worker_id_arg, new_slot):
        return None

    async def mock_scalar(stmt):
        scalar_calls.append(stmt)
        if len(scalar_calls) == 1:
            return existing
        return existing

    class DummySession:
        async def scalar(self, stmt):
            return await mock_scalar(stmt)

        async def flush(self) -> None:
            return None

    monkeypatch.setattr(application_service, "_get_shift_slot", mock_get_shift_slot)
    monkeypatch.setattr(application_service.matching_service, "get_vacancy_for_worker", mock_get_vacancy_for_worker)
    monkeypatch.setattr(application_service, "has_shift_conflict", mock_has_shift_conflict)

    result = await application_service.apply_to_shift(DummySession(), Worker(), slot_id)

    assert existing.status == ApplicationStatus.pending
    assert existing.cancelled_at is None
    assert result.status == ApplicationStatus.pending
    assert result.job_title == "Официант"


@pytest.mark.asyncio
async def test_apply_to_shift_blocked_for_unverified_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.db.models import VerificationStatus
    from app.services import application_service

    class Worker:
        id = uuid4()
        verification_status = VerificationStatus.pending

    slot_id = uuid4()

    async def mock_get_shift_slot(session, shift_slot_id):
        return object()

    class DummySession:
        pass

    monkeypatch.setattr(application_service, "_get_shift_slot", mock_get_shift_slot)

    with pytest.raises(application_service.WorkerNotVerifiedError) as exc_info:
        await application_service.apply_to_shift(DummySession(), Worker(), slot_id)

    assert "не верифицирован" in str(exc_info.value).lower()
