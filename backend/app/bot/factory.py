from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.applications import router as applications_router
from app.bot.handlers.job_request import router as job_request_router
from app.bot.handlers.notifications import router as notifications_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.vacancy_search import router as vacancy_search_router
from app.bot.handlers.worker_registration import router as worker_registration_router
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.core.config import Settings, get_settings


def create_bot(settings: Settings | None = None) -> Bot:
    resolved = settings or get_settings()
    return Bot(
        token=resolved.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(admin_router)
    dp.include_router(worker_registration_router)
    dp.include_router(applications_router)
    dp.include_router(vacancy_search_router)
    dp.include_router(job_request_router)
    dp.include_router(notifications_router)
    dp.include_router(start_router)
    return dp
