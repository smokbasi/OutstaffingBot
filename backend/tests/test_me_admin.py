from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User, UserRole
from app.main import app
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
ADMIN_TELEGRAM_ID = 999888777
REGULAR_TELEGRAM_ID = 111222333


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=ADMIN_TELEGRAM_ID,
        username="admin",
        role=UserRole.admin,
    )


@pytest.fixture
def regular_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=REGULAR_TELEGRAM_ID,
        username="user",
        role=UserRole.worker,
    )


@pytest.fixture
async def me_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_telegram_ids", [ADMIN_TELEGRAM_ID])

    transport = ASGITransport(app=app)

    async def make_client(user: User) -> AsyncClient:
        async def override_user():
            return user

        app.dependency_overrides[get_current_user] = override_user
        init_data = build_test_init_data(
            TEST_BOT_TOKEN,
            user.telegram_id,
            username=user.username or "user",
        )
        client = AsyncClient(transport=transport, base_url="http://test")
        client.headers["Authorization"] = f"tma {init_data}"
        return client

    yield make_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_me_is_admin_true(me_client, admin_user: User):
    async with await me_client(admin_user) as client:
        response = await client.get("/api/v1/me")
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert data["telegram_id"] == ADMIN_TELEGRAM_ID


@pytest.mark.asyncio
async def test_me_is_admin_false(me_client, regular_user: User):
    async with await me_client(regular_user) as client:
        response = await client.get("/api/v1/me")
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is False
    assert data["telegram_id"] == REGULAR_TELEGRAM_ID
