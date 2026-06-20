import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.start import router as start_router
from app.bot.menu_setup import setup_default_mini_app_menu
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
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

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
