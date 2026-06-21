from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.models import Gender, User, UserRole, Worker
from app.db.session import get_db_session
from app.main import app
from app.schemas.preferences import WorkerPreferencesRead
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=12345,
        username="worker1",
        role=UserRole.worker,
    )


@pytest.fixture
def sample_preferences() -> WorkerPreferencesRead:
    return WorkerPreferencesRead(
        category_ids=[2],
        metro_station_ids=[1],
        min_hourly_rate=Decimal("400.00"),
        notifications_enabled=True,
    )


@pytest.fixture
async def client(test_user: User, monkeypatch: pytest.MonkeyPatch):
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()

    async def override_user():
        return test_user

    async def override_session():
        class DummySession:
            async def commit(self) -> None:
                return None

        yield DummySession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    app.dependency_overrides.clear()
    config.get_settings.cache_clear()


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 12345)}"}


@pytest.mark.asyncio
async def test_get_preferences(client: AsyncClient, sample_preferences: WorkerPreferencesRead, monkeypatch):
    from app.services import preferences_service

    async def fake_get(_session, _user):
        return sample_preferences

    monkeypatch.setattr(preferences_service, "get_preferences", fake_get)

    response = await client.get("/api/v1/worker/preferences", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["category_ids"] == [2]
    assert body["notifications_enabled"] is True


@pytest.mark.asyncio
async def test_update_preferences(client: AsyncClient, sample_preferences: WorkerPreferencesRead, monkeypatch):
    from app.services import preferences_service

    async def fake_upsert(_session, _user, data):
        return WorkerPreferencesRead(
            category_ids=data.category_ids or [],
            metro_station_ids=data.metro_station_ids or [],
            min_hourly_rate=data.min_hourly_rate,
            notifications_enabled=data.notifications_enabled if data.notifications_enabled is not None else True,
        )

    monkeypatch.setattr(preferences_service, "upsert_preferences", fake_upsert)

    response = await client.put(
        "/api/v1/worker/preferences",
        headers=_auth_headers(),
        json={
            "category_ids": [2, 5],
            "metro_station_ids": [1],
            "min_hourly_rate": "500",
            "notifications_enabled": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_ids"] == [2, 5]
    assert body["notifications_enabled"] is False


@pytest.mark.asyncio
async def test_toggle_notifications(client: AsyncClient, monkeypatch):
    from app.services import preferences_service

    async def fake_set(_session, _user, *, enabled: bool):
        return WorkerPreferencesRead(
            category_ids=[],
            metro_station_ids=[],
            min_hourly_rate=None,
            notifications_enabled=enabled,
        )

    monkeypatch.setattr(preferences_service, "set_notifications_enabled", fake_set)

    response = await client.patch(
        "/api/v1/worker/notifications",
        headers=_auth_headers(),
        json={"notifications_enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["notifications_enabled"] is False
