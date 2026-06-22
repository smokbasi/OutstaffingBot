import asyncio
import logging
import signal

from app.bot.factory import create_bot, create_dispatcher
from app.bot.menu_setup import setup_default_mini_app_menu
from app.bot.startup_announcement import announce_bot_update
from app.bot.webhook_setup import register_telegram_webhook
from app.core.config import get_settings
from app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def run_polling() -> None:
    settings = get_settings()
    bot = create_bot(settings)
    dp = create_dispatcher()
    dp.startup.register(setup_default_mini_app_menu)
    dp.startup.register(announce_bot_update)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


async def run_webhook_register_daemon() -> None:
    settings = get_settings()
    await register_telegram_webhook(settings)
    logger.info("Webhook registered; updates are handled by the API service")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()


async def run_bot() -> None:
    settings = get_settings()
    setup_logging(log_level=settings.log_level, app_env=settings.app_env)

    if not settings.bot_enabled:
        logger.warning(
            "BOT_TOKEN is not set — dry-run mode. Set BOT_TOKEN in .env to start the bot."
        )
        return

    if settings.webhook_enabled:
        await run_webhook_register_daemon()
        return

    await run_polling()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
