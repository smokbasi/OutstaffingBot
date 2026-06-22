from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import Employer, User, UserRole, VerificationStatus
from app.schemas.employer import EmployerProfileRead
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


def test_employer_model_uses_verification_status_column() -> None:
    """Regression: staging 500 when ORM still mapped employers.verified after migration 003."""
    column_names = {column.key for column in Employer.__table__.columns}
    assert "verification_status" in column_names
    assert "verified" not in column_names


@pytest.mark.asyncio
async def test_me_with_employer_profile(
    me_client,
    regular_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    employer_id = uuid4()

    async def mock_get_employer_profile(_session, _user: User) -> EmployerProfileRead:
        return EmployerProfileRead(
            id=employer_id,
            company_name="ООО Тест",
            contact_phone="+79990001122",
            contact_person="Иван",
            verification_status=VerificationStatus.verified,
        )

    monkeypatch.setattr(
        "app.services.employer_service.get_employer_profile",
        mock_get_employer_profile,
    )

    async with await me_client(regular_user) as client:
        response = await client.get("/api/v1/me")

    assert response.status_code == 200
    data = response.json()
    assert data["has_employer_profile"] is True
