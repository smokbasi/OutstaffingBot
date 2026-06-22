import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.applications import router as applications_router
from app.api.routes.employer import router as employer_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.reference import router as reference_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.webhook import router as webhook_router
from app.api.routes.worker import router as worker_router
from app.api.routes.worker_vacancies import router as worker_vacancies_router
from app.bot.factory import create_bot, create_dispatcher
from app.bot.menu_setup import setup_default_mini_app_menu
from app.bot.startup_announcement import announce_bot_update
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.sentry import init_sentry

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(log_level=settings.log_level, app_env=settings.app_env)
    init_sentry(settings)

    if settings.webhook_enabled:
        bot = create_bot(settings)
        dp = create_dispatcher()
        dp.startup.register(setup_default_mini_app_menu)
        dp.startup.register(announce_bot_update)
        await dp.emit_startup(bot)
        app.state.webhook_bot = bot
        app.state.webhook_dp = dp
        logger.info("Webhook mode: dispatcher ready (url=%s)", settings.webhook_url)
    else:
        app.state.webhook_bot = None
        app.state.webhook_dp = None

    yield

    if app.state.webhook_bot is not None:
        await app.state.webhook_bot.session.close()


app = FastAPI(
    title="OutstaffingBot API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.mini_app_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(webhook_router, tags=["webhook"])
for api_prefix in ("/api/v1", "/v1"):
    app.include_router(me_router, prefix=api_prefix)
    app.include_router(worker_router, prefix=api_prefix)
    app.include_router(worker_vacancies_router, prefix=api_prefix)
    app.include_router(applications_router, prefix=api_prefix)
    app.include_router(employer_router, prefix=api_prefix)
    app.include_router(admin_router, prefix=api_prefix)
    app.include_router(reviews_router, prefix=api_prefix)
    app.include_router(reference_router, prefix=api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "outstaffing-api", "status": "ok"}
