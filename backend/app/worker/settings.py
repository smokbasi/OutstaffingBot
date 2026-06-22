from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.worker import tasks


async def worker_startup(ctx: dict) -> None:
    settings = get_settings()
    if settings.bot_enabled:
        ctx["bot"] = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )


async def worker_shutdown(ctx: dict) -> None:
    bot = ctx.get("bot")
    if bot is not None:
        await bot.session.close()


class WorkerSettings:
    functions = [
        tasks.match_workers_for_job,
        tasks.post_job_to_groups,
        tasks.close_group_posts,
    ]
    on_startup = worker_startup
    on_shutdown = worker_shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 120
