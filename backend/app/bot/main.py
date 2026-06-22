import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.admin_groups import router as admin_groups_router
from app.bot.handlers.notifications import router as notifications_router
from app.bot.handlers.applications import router as applications_router
from app.bot.handlers.job_request import router as job_request_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.vacancy_search import router as vacancy_search_router
from app.bot.handlers.worker_registration import router as worker_registration_router
from app.bot.menu_setup import setup_default_mini_app_menu
from app.bot.startup_announcement import announce_bot_update
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(admin_groups_router)
    dp.include_router(worker_registration_router)
    dp.include_router(applications_router)
    dp.include_router(vacancy_search_router)
    dp.include_router(job_request_router)
    dp.include_router(notifications_router)
    dp.include_router(start_router)
    return dp


async def run_bot() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, stream=sys.stdout)

    if not settings.bot_enabled:
        logger.warning(
            "BOT_TOKEN is not set — dry-run mode. Set BOT_TOKEN in .env to start polling."
        )
        return

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()
    dp.startup.register(setup_default_mini_app_menu)
    dp.startup.register(announce_bot_update)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
