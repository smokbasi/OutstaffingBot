from fastapi import Depends, HTTPException

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.models import User


async def get_current_admin(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> User:
    if user.telegram_id not in settings.admin_telegram_ids:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
