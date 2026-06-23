from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Application, ApplicationStatus, Employer, JobRequest, Review, ReviewerRole, User, Worker
from app.schemas.review import ReviewCreate, ReviewRead


class ReviewError(Exception):
    pass


class ReviewNotAllowedError(ReviewError):
    pass


class ReviewAlreadyExistsError(ReviewError):
    pass


class ApplicationNotReviewableError(ReviewError):
    pass


def _review_to_read(review: Review) -> ReviewRead:
    return ReviewRead(
        id=review.id,
        application_id=review.application_id,
        reviewer_user_id=review.reviewer_user_id,
        reviewed_user_id=review.reviewed_user_id,
        reviewer_role=review.reviewer_role,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


async def create_review(
    session: AsyncSession,
    user: User,
    data: ReviewCreate,
) -> ReviewRead:
    app = await session.scalar(
        select(Application)
        .options(
            selectinload(Application.job_request).selectinload(JobRequest.employer),
            selectinload(Application.worker).selectinload(Worker.user),
        )
        .where(Application.id == data.application_id)
    )
    if app is None or app.job_request is None or app.worker is None:
        raise ApplicationNotReviewableError("Application not found")

    if app.status != ApplicationStatus.accepted:
        raise ApplicationNotReviewableError("Review only after accepted application")

    employer = app.job_request.employer
    worker = app.worker
    if employer is None:
        raise ApplicationNotReviewableError("Employer not found")

    if data.reviewer_role == ReviewerRole.worker:
        if worker.user_id != user.id:
            raise ReviewNotAllowedError("Only the worker can leave this review")
        reviewed_user_id = employer.user_id
    else:
        if employer.user_id != user.id:
            raise ReviewNotAllowedError("Only the employer can leave this review")
        reviewed_user_id = worker.user_id

    existing = await session.scalar(
        select(Review).where(
            Review.application_id == data.application_id,
            Review.reviewer_user_id == user.id,
        )
    )
    if existing is not None:
        raise ReviewAlreadyExistsError("Review already submitted")

    review = Review(
        application_id=data.application_id,
        reviewer_user_id=user.id,
        reviewed_user_id=reviewed_user_id,
        reviewer_role=data.reviewer_role,
        rating=data.rating,
        comment=data.comment,
    )
    session.add(review)
    await session.flush()
    return _review_to_read(review)


async def list_reviews_for_user(session: AsyncSession, user_id: UUID) -> list[ReviewRead]:
    result = await session.scalars(
        select(Review)
        .where(Review.reviewed_user_id == user_id)
        .order_by(Review.created_at.desc())
    )
    return [_review_to_read(r) for r in result.all()]
