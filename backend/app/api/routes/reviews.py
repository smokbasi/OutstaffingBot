from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.review import ReviewCreate, ReviewRead
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewRead, status_code=201)
async def create_review(
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewRead:
    try:
        review = await review_service.create_review(session, user, data)
    except review_service.ApplicationNotReviewableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except review_service.ReviewNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except review_service.ReviewAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return review


@router.get("/me", response_model=list[ReviewRead])
async def list_my_reviews(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReviewRead]:
    return await review_service.list_reviews_for_user(session, user.id)
