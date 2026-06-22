from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.db.models import JobRequestStatus
from app.schemas.job_request import JobRequestUpdate
from app.services import job_service


@pytest.mark.asyncio
async def test_activate_job_enqueues_match_task(monkeypatch):
    job_id = uuid4()
    employer_id = uuid4()
    now = datetime.now(timezone.utc)

    class FakeJob:
        def __init__(self, status: JobRequestStatus):
            self.id = job_id
            self.status = status
            self.notify_matching_workers = True
            self.employer_id = employer_id
            self.category_id = 1
            self.title = "Тест"
            self.description = "Описание"
            self.metro_station_id = 1
            self.hourly_rate = Decimal("400")
            self.workers_needed = 1
            self.min_experience_months = None
            self.required_gender = None
            self.min_age = None
            self.max_age = None
            self.dress_code = None
            self.contact_info = None
            self.post_to_groups = False
            self.address = None
            self.includes_lunch = False
            self.created_at = now
            self.updated_at = now
            self.shift_slots = []
            self.category = None
            self.metro_station = None

    fake_job = FakeJob(JobRequestStatus.draft)
    active_job = FakeJob(JobRequestStatus.active)

    async def fake_scalar(stmt):
        if fake_job.status == JobRequestStatus.draft:
            return fake_job
        return active_job

    class DummySession:
        async def flush(self):
            fake_job.status = JobRequestStatus.active

        async def scalar(self, stmt):
            return await fake_scalar(stmt)

    enqueue_mock = AsyncMock(return_value="job-123")
    monkeypatch.setattr(job_service, "enqueue_job", enqueue_mock)

    await job_service.update_job_request(
        DummySession(),
        employer_id,
        job_id,
        JobRequestUpdate(status=JobRequestStatus.active),
    )

    enqueue_mock.assert_awaited_once_with("match_workers_for_job", str(job_id))
