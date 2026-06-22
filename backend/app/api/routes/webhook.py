import logging

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.bot.factory import create_bot, create_dispatcher
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    if not settings.webhook_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook disabled")

    if secret != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    bot = request.app.state.webhook_bot
    dp = request.app.state.webhook_dp
    payload = await request.json()
    update = Update.model_validate(payload, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}
