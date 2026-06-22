from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.models import Gender, User, UserRole, VerificationStatus
from app.db.session import get_db_session
from app.main import app
from app.schemas.worker import WorkerProfileRead, WorkerExperienceRead
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
def sample_profile() -> WorkerProfileRead:
    worker_id = uuid4()
    exp_id = uuid4()
    return WorkerProfileRead(
        id=worker_id,
        first_name="Иван",
        last_name="Петров",
        age=25,
        gender=Gender.male,
        metro_station_id=1,
        metro_station_name="Автово",
        min_hourly_rate=Decimal("350.00"),
        resume_completed=True,
        verification_status=VerificationStatus.verified,
        experiences=[
            WorkerExperienceRead(
                id=exp_id,
                category_id=1,
                category_name="Официант",
                role_title="Официант зала",
                duration_months=12,
                description=None,
            )
        ],
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


@pytest.mark.asyncio
async def test_get_worker_profile_not_found(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_profile(session, user):
        return None

    monkeypatch.setattr("app.api.routes.worker.worker_service.get_worker_profile", mock_get_profile)
    response = await client.get(
        "/api/v1/worker/profile",
        headers={"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 12345)}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_worker_profile_success(
    client: AsyncClient, sample_profile: WorkerProfileRead, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_profile(session, user):
        return sample_profile

    monkeypatch.setattr("app.api.routes.worker.worker_service.get_worker_profile", mock_get_profile)
    response = await client.get(
        "/api/v1/worker/profile",
        headers={"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 12345)}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert len(data["experiences"]) == 1


@pytest.mark.asyncio
async def test_put_worker_profile(client: AsyncClient, sample_profile: WorkerProfileRead, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_upsert(session, user, data, resume_completed=None):
        return sample_profile

    monkeypatch.setattr("app.api.routes.worker.worker_service.upsert_worker_profile", mock_upsert)
    response = await client.put(
        "/api/v1/worker/profile",
        headers={"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 12345)}"},
        json={
            "first_name": "Иван",
            "last_name": "Петров",
            "age": 25,
            "gender": "male",
            "metro_station_id": 1,
            "min_hourly_rate": "350.00",
        },
    )
    assert response.status_code == 200
    assert response.json()["resume_completed"] is True


@pytest.mark.asyncio
async def test_worker_profile_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()
    app.dependency_overrides.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        response = await http_client.get("/api/v1/worker/profile")

    config.get_settings.cache_clear()
    assert response.status_code == 422
