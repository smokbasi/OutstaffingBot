from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User, UserRole
from app.db.session import get_db_session
from app.main import app
from app.services import admin_service, audit_service
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
ADMIN_TELEGRAM_ID = 999888777


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=ADMIN_TELEGRAM_ID,
        username="admin",
        role=UserRole.admin,
    )


@pytest.fixture
async def admin_client(admin_user: User, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    get_settings.cache_clear()

    settings = get_settings()
    monkeypatch.setattr(settings, "admin_telegram_ids", [ADMIN_TELEGRAM_ID])

    async def override_user():
        return admin_user

    async def override_session():
        yield None

    app.dependency_overrides[get_current_user] = override_user

    transport = ASGITransport(app=app)
    init_data = build_test_init_data(TEST_BOT_TOKEN, admin_user.telegram_id, username=admin_user.username or "admin")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"tma {init_data}"
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_stats_endpoint_mocked(monkeypatch, admin_client: AsyncClient):
    from app.schemas.admin import AdminStats

    async def fake_stats(session):
        return AdminStats(workers_count=10, employers_count=5, jobs_count=3, pending_verifications=2)

    monkeypatch.setattr(admin_service, "get_admin_stats", fake_stats)

    response = await admin_client.get("/api/v1/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["workers_count"] == 10
    assert data["pending_verifications"] == 2


@pytest.mark.asyncio
async def test_admin_forbidden_for_non_admin(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_telegram_ids", [ADMIN_TELEGRAM_ID])

    regular_user = User(id=uuid4(), telegram_id=111222333, username="user", role=UserRole.worker)

    async def override_user():
        return regular_user

    app.dependency_overrides[get_current_user] = override_user
    init_data = build_test_init_data(TEST_BOT_TOKEN, regular_user.telegram_id, username=regular_user.username or "user")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"tma {init_data}"},
        )
    assert response.status_code == 403
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_format_audit_entry():
    from datetime import datetime, timezone
    from app.db.models import AuditLog

    entry = AuditLog(
        id=uuid4(),
        actor_id=uuid4(),
        action="job.create",
        entity_type="job_request",
        entity_id=str(uuid4()),
        metadata_={"status": "draft"},
        created_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
    )
    text = audit_service.format_audit_entry(entry)
    assert "job.create" in text
    assert "job_request" in text
