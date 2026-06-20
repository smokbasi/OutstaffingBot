from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="OutstaffingBot API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "development" else None,
)

app.include_router(health_router, tags=["health"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "outstaffing-api", "status": "ok"}
