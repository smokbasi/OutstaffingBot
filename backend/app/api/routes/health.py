from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import async_session_factory

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "mode": "webhook" if settings.webhook_enabled else "polling",
    }


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        redis = get_redis()
        await redis.ping()
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "detail": str(exc)},
        )
    return JSONResponse(content={"status": "ready"})
