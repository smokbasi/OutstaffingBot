from uuid import uuid4

import pytest

from app.services import job_service


class FakeEmployer:
    def __init__(self, *, is_banned: bool = False):
        self.id = uuid4()
        self.is_banned = is_banned


class FakeSession:
    def __init__(self, employer: FakeEmployer | None):
        self.employer = employer

    async def scalar(self, stmt):
        return self.employer


@pytest.mark.asyncio
async def test_create_job_request_blocked_for_banned_employer() -> None:
    employer = FakeEmployer(is_banned=True)
    session = FakeSession(employer)

    with pytest.raises(ValueError, match="заблокирован"):
        await job_service.create_job_request(
            session,
            employer.id,
            data=object(),  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_update_job_request_activate_blocked_for_banned_employer() -> None:
    from app.db.models import JobRequestStatus
    from app.schemas.job_request import JobRequestUpdate

    employer = FakeEmployer(is_banned=True)
    job_id = uuid4()

    class Job:
        id = job_id
        status = JobRequestStatus.draft
        notify_matching_workers = False

    call_count = 0

    class Session:
        async def scalar(self, stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Job()
            return employer

    with pytest.raises(ValueError, match="заблокирован"):
        await job_service.update_job_request(
            Session(),
            employer.id,
            job_id,
            JobRequestUpdate(status=JobRequestStatus.active),
        )
