"""Regression tests for staging 500s: missing import and metro scope bug."""

from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models import (
    JobCategory,
    JobRequest,
    JobRequestStatus,
    MetroStation,
    ShiftSlot,
    User,
    UserRole,
    Worker,
)
from app.schemas.job_request import JobRequestCreate, ShiftSlotCreate
from app.services.job_service import create_job_request
from app.services.preferences_service import get_preferences


@pytest.mark.asyncio
async def test_get_preferences_imports_select(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /worker/preferences failed with NameError: select is not defined."""
    user = User(id=uuid4(), telegram_id=12345, role=UserRole.worker)
    worker = Worker(
        id=uuid4(),
        user_id=user.id,
        notifications_enabled=False,
    )

    async def fake_get_worker(_session, _user_id):
        return worker

    monkeypatch.setattr(
        "app.services.preferences_service.get_worker_by_user_id",
        fake_get_worker,
    )

    class DummySession:
        async def scalar(self, _stmt):
            return None

    result = await get_preferences(DummySession(), user)
    assert result.category_ids == []
    assert result.metro_station_ids == []
    assert result.min_hourly_rate is None
    assert result.notifications_enabled is False


@pytest.mark.asyncio
async def test_create_job_request_uses_metro_city(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /employer/jobs failed with NameError: metro_exists is not defined."""
    employer_id = uuid4()
    metro = MetroStation(id=1, name="Автово", line_name="Красная", city="spb")
    category = JobCategory(id=1, slug="waiter", name_ru="Официант")
    now = datetime.now(timezone.utc)

    data = JobRequestCreate(
        category_id=1,
        title="Официант на смену",
        description="Обслуживание зала",
        metro_station_id=1,
        hourly_rate=Decimal("400.00"),
        workers_needed=2,
        shift_slots=[
            ShiftSlotCreate(
                shift_date=date(2026, 6, 25),
                start_time=time(10, 0),
                end_time=time(22, 0),
            )
        ],
    )

    created_job: JobRequest | None = None
    created_slots: list[ShiftSlot] = []
    scalar_queue: list[object | None] = [1, metro]

    class DummySession:
        def add(self, obj) -> None:
            nonlocal created_job
            if isinstance(obj, JobRequest):
                obj.id = uuid4()
                obj.created_at = now
                obj.updated_at = now
                obj.status = JobRequestStatus.draft
                created_job = obj
            elif isinstance(obj, ShiftSlot):
                obj.id = uuid4()
                obj.slots_filled = obj.slots_filled or 0
                created_slots.append(obj)

        async def scalar(self, _stmt):
            if scalar_queue:
                return scalar_queue.pop(0)
            assert created_job is not None
            created_job.category = category
            created_job.metro_station = metro
            created_job.shift_slots = created_slots
            return created_job

        async def flush(self) -> None:
            return None

    result = await create_job_request(
        DummySession(),
        employer_id,
        data,
        actor_id=uuid4(),
    )

    assert created_job is not None
    assert created_job.city == "spb"
    assert result.city == "spb"
    assert result.status == JobRequestStatus.draft
    assert len(result.shift_slots) == 1
