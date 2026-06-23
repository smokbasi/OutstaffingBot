from uuid import uuid4

import pytest

from app.db.models import ApplicationStatus, ReviewerRole
from app.schemas.review import ReviewCreate
from app.services.review_service import (
    ApplicationNotReviewableError,
    ReviewNotAllowedError,
    create_review,
)


class FakeUser:
    def __init__(self, user_id=None):
        self.id = user_id or uuid4()


class FakeEmployer:
    def __init__(self, user_id):
        self.user_id = user_id


class FakeWorker:
    def __init__(self, user_id):
        self.user_id = user_id
        self.id = uuid4()


class FakeJob:
    def __init__(self, employer):
        self.employer = employer


class FakeApplication:
    def __init__(self, status, worker_user_id, employer_user_id):
        self.id = uuid4()
        self.job_request_id = uuid4()
        self.status = status
        self.worker = FakeWorker(worker_user_id)
        self.job_request = FakeJob(FakeEmployer(employer_user_id))


class FakeSession:
    def __init__(self, app):
        self.app = app

    async def scalar(self, stmt):
        return self.app

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_review_rejected_if_not_accepted():
    worker_user = FakeUser()
    employer_user = FakeUser()
    app = FakeApplication(ApplicationStatus.pending, worker_user.id, employer_user.id)
    session = FakeSession(app)
    user = worker_user
    data = ReviewCreate(
        application_id=app.id,
        reviewer_role=ReviewerRole.worker,
        rating=5,
    )
    with pytest.raises(ApplicationNotReviewableError):
        await create_review(session, user, data)


@pytest.mark.asyncio
async def test_review_not_allowed_wrong_user():
    worker_user = FakeUser()
    employer_user = FakeUser()
    app = FakeApplication(ApplicationStatus.accepted, worker_user.id, employer_user.id)
    session = FakeSession(app)
    wrong_user = FakeUser()
    data = ReviewCreate(
        application_id=app.id,
        reviewer_role=ReviewerRole.worker,
        rating=4,
    )
    with pytest.raises(ReviewNotAllowedError):
        await create_review(session, wrong_user, data)
