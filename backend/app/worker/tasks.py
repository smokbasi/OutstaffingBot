import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.services import notification_service

logger = logging.getLogger(__name__)


async def match_workers_for_job(ctx: dict, job_id: str) -> int:
    settings = get_settings()
    if not settings.bot_enabled:
        logger.warning("BOT_TOKEN not set — skip notify for job %s", job_id)
        return 0

    bot = ctx.get("bot")
    if bot is None:
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    from uuid import UUID

    async with async_session_factory() as session:
        sent = await notification_service.notify_matching_workers(
            session,
            bot,
            settings,
            UUID(job_id),
        )
async def notify_employers_for_worker(ctx: dict, worker_id: str) -> int:
    settings = get_settings()
    if not settings.bot_enabled:
        logger.warning("BOT_TOKEN not set — skip employer notify for worker %s", worker_id)
        return 0

    bot = ctx.get("bot")
    if bot is None:
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    from uuid import UUID

    async with async_session_factory() as session:
        sent = await notification_service.notify_employers_for_worker(
            session,
            bot,
            settings,
            UUID(worker_id),
        )
    logger.info("Notified %s employers for worker %s", sent, worker_id)
    return sent
