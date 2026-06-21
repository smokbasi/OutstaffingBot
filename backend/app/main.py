from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.reference import router as reference_router
from app.api.routes.worker import router as worker_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="OutstaffingBot API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.mini_app_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
for api_prefix in ("/api/v1", "/v1"):
    app.include_router(me_router, prefix=api_prefix)
    app.include_router(worker_router, prefix=api_prefix)
    app.include_router(reference_router, prefix=api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "outstaffing-api", "status": "ok"}
