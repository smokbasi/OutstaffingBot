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
