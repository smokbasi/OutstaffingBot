import logging

from app.bot.factory import create_bot
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


async def register_telegram_webhook(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    if not resolved.webhook_enabled:
        raise RuntimeError("WEBHOOK_URL and WEBHOOK_SECRET must be set for webhook registration")

    bot = create_bot(resolved)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(
            url=resolved.webhook_url,
            secret_token=resolved.webhook_secret,
            allowed_updates=resolved.webhook_allowed_updates,
        )
        webhook_info = await bot.get_webhook_info()
        logger.info(
            "Telegram webhook registered: url=%s pending=%s",
            webhook_info.url,
            webhook_info.pending_update_count,
        )
    finally:
        await bot.session.close()


async def delete_telegram_webhook(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    if not resolved.bot_enabled:
        return
    bot = create_bot(resolved)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Telegram webhook removed (polling mode)")
    finally:
        await bot.session.close()
