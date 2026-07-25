from datetime import date, time
from uuid import uuid4

import pytest

from app.db.models import JobRequestStatus
from app.services.job_service import job_has_upcoming_shifts, job_is_historical


class _ShiftSlot:
    def __init__(self, shift_date: date) -> None:
        self.shift_date = shift_date


class _Job:
    def __init__(
        self,
        *,
        status: JobRequestStatus = JobRequestStatus.active,
        shift_dates: list[date] | None = None,
    ) -> None:
        self.id = uuid4()
        self.status = status
        self.shift_slots = [_ShiftSlot(value) for value in (shift_dates or [])]


def test_job_has_upcoming_shifts_when_future_shift_exists() -> None:
    job = _Job(shift_dates=[date(2026, 7, 6), date(2026, 7, 10)])
    assert job_has_upcoming_shifts(job, today=date(2026, 7, 7)) is True


def test_job_has_upcoming_shifts_when_only_past_shifts() -> None:
    job = _Job(shift_dates=[date(2026, 7, 4), date(2026, 7, 6)])
    assert job_has_upcoming_shifts(job, today=date(2026, 7, 7)) is False


def test_job_has_upcoming_shifts_includes_today() -> None:
    job = _Job(shift_dates=[date(2026, 7, 7)])
    assert job_has_upcoming_shifts(job, today=date(2026, 7, 7)) is True


def test_job_has_upcoming_shifts_without_slots() -> None:
    job = _Job(shift_dates=[])
    assert job_has_upcoming_shifts(job, today=date(2026, 7, 7)) is True


def test_job_is_historical_for_past_active_job() -> None:
    job = _Job(status=JobRequestStatus.active, shift_dates=[date(2026, 7, 4)])
    assert job_is_historical(job, today=date(2026, 7, 7)) is True


def test_job_is_historical_for_active_job_with_future_shift() -> None:
    job = _Job(status=JobRequestStatus.active, shift_dates=[date(2026, 7, 4), date(2026, 7, 10)])
    assert job_is_historical(job, today=date(2026, 7, 7)) is False


@pytest.mark.parametrize(
    "status",
    [
        JobRequestStatus.cancelled,
        JobRequestStatus.filled,
        JobRequestStatus.expired,
    ],
)
def test_job_is_historical_for_terminal_status(status: JobRequestStatus) -> None:
    job = _Job(status=status, shift_dates=[date(2026, 12, 31)])
    assert job_is_historical(job, today=date(2026, 7, 7)) is True


def test_job_is_historical_for_draft_with_past_shifts() -> None:
    job = _Job(status=JobRequestStatus.draft, shift_dates=[date(2026, 7, 4)])
    assert job_is_historical(job, today=date(2026, 7, 7)) is False
