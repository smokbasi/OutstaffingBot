from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_db_session

router = APIRouter(tags=["me"])


class MeResponse(BaseModel):
    id: str
    telegram_id: int
    username: str | None
    role: str
    has_worker_profile: bool
    has_employer_profile: bool
    is_admin: bool


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> MeResponse:
    from app.services import employer_service, worker_service

    worker_profile = await worker_service.get_worker_profile(session, user)
    employer_profile = await employer_service.get_employer_profile(session, user)
    return MeResponse(
        id=str(user.id),
        telegram_id=user.telegram_id,
        username=user.username,
        role=user.role.value,
        has_worker_profile=worker_profile is not None and worker_profile.resume_completed,
        has_employer_profile=employer_profile is not None,
        is_admin=user.telegram_id in settings.admin_telegram_ids,
    )
