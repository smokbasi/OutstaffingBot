from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session

router = APIRouter(tags=["me"])


class MeResponse(BaseModel):
    id: str
    telegram_id: int
    username: str | None
    role: str
    has_worker_profile: bool


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    from app.services import worker_service

    profile = await worker_service.get_worker_profile(session, user)
    return MeResponse(
        id=str(user.id),
        telegram_id=user.telegram_id,
        username=user.username,
        role=user.role.value,
        has_worker_profile=profile is not None and profile.resume_completed,
    )
