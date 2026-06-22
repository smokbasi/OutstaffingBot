from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.db.models import (
    Application,
    ApplicationStatus,
    JobCategory,
    JobRequest,
    JobRequestStatus,
    MetroStation,
    ShiftSlot,
    Worker,
)
from app.services import application_service


def _make_application(*, status: ApplicationStatus = ApplicationStatus.accepted) -> Application:
    job_id = uuid4()
    slot_id = uuid4()
    job = JobRequest(
        id=job_id,
        employer_id=uuid4(),
        category_id=2,
        title="Официант",
        description="Смена",
        metro_station_id=1,
        hourly_rate=Decimal("350"),
        workers_needed=2,
        status=JobRequestStatus.active,
        post_to_groups=True,
    )
    job.category = JobCategory(id=2, slug="waiter", name_ru="Официант")
    job.metro_station = MetroStation(id=1, name="Сокольники", line_name="Красная")
    slot = ShiftSlot(
        id=slot_id,
        job_request_id=job_id,
        shift_date=date(2026, 6, 20),
        start_time=time(10, 0),
        end_time=time(22, 0),
        slots_total=2,
        slots_filled=1,
    )
    app = Application(
        id=uuid4(),
        worker_id=uuid4(),
        job_request_id=job_id,
        shift_slot_id=slot_id,
        status=status,
        applied_at=datetime.now(timezone.utc),
    )
    app.shift_slot = slot
    app.job_request = job
    return app


@pytest.mark.asyncio
async def test_cancel_accepted_application_enqueues_group_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = Worker(id=uuid4(), user_id=uuid4())
    app = _make_application(status=ApplicationStatus.accepted)
    enqueue_mock = AsyncMock(return_value="job-1")

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=app)
    session.flush = AsyncMock()
    monkeypatch.setattr(application_service, "enqueue_job", enqueue_mock)

    await application_service.cancel_application(session, worker, app.id)

    enqueue_mock.assert_awaited_once_with("sync_group_posts_for_headcount", str(app.job_request_id))


@pytest.mark.asyncio
async def test_cancel_pending_application_enqueues_group_sync_when_post_to_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = Worker(id=uuid4(), user_id=uuid4())
    app = _make_application(status=ApplicationStatus.pending)
    enqueue_mock = AsyncMock(return_value="job-1")

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=app)
    session.flush = AsyncMock()
    monkeypatch.setattr(application_service, "enqueue_job", enqueue_mock)

    await application_service.cancel_application(session, worker, app.id)

    enqueue_mock.assert_awaited_once_with("sync_group_posts_for_headcount", str(app.job_request_id))


@pytest.mark.asyncio
async def test_accept_application_enqueues_group_sync_when_headcount_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    employer_id = uuid4()
    app = _make_application(status=ApplicationStatus.pending)
    app.job_request.employer_id = employer_id
    app.shift_slot.slots_filled = 1
    enqueue_mock = AsyncMock(return_value="job-1")

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=app)
    session.flush = AsyncMock()
    monkeypatch.setattr(application_service, "enqueue_job", enqueue_mock)
    monkeypatch.setattr(
        application_service,
        "count_accepted_applications",
        AsyncMock(return_value=2),
    )

    await application_service.accept_application(session, employer_id, app.id)

    enqueue_mock.assert_awaited_once_with("sync_group_posts_for_headcount", str(app.job_request_id))
