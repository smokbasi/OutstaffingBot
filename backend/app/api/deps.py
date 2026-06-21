from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.init_data import InitDataError, validate_init_data
from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.services import user_service


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Invalid auth scheme")

    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="Bot token not configured")

    init_data = authorization[4:]
    try:
        tg_user = validate_init_data(init_data, settings.bot_token)
    except InitDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    user = await user_service.get_or_create_by_telegram_id(
        session,
        int(tg_user["id"]),
        username=tg_user.get("username"),
        language_code=tg_user.get("language_code"),
    )
    return user
