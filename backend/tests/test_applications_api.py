from datetime import datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.models import ApplicationStatus, Gender, User, UserRole
from app.db.session import get_db_session
from app.main import app
from app.schemas.application import ApplicationListResponse, ApplicationRead
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
def sample_application() -> ApplicationRead:
    from datetime import date

    return ApplicationRead(
        id=uuid4(),
        job_request_id=uuid4(),
        shift_slot_id=uuid4(),
        status=ApplicationStatus.pending,
        applied_at=datetime.now(timezone.utc),
        cancelled_at=None,
        job_title="Официант на смену",
        category_name="Официант",
        metro_station_name="Автово",
        hourly_rate="400.00",
        shift_date=date(2026, 6, 25),
        start_time=time(10, 0),
        end_time=time(22, 0),
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
async def test_apply_success(
    client: AsyncClient,
    sample_application: ApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()

    shift_slot_id = uuid4()

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_apply(session, worker, slot_id, *, cancel_conflicting_id=None):
        assert slot_id == shift_slot_id
        return sample_application

    monkeypatch.setattr("app.api.routes.applications.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr("app.api.routes.applications.application_service.apply_to_shift", mock_apply)

    response = await client.post(
        "/api/v1/applications",
        headers=_auth_headers(),
        json={"shift_slot_id": str(shift_slot_id)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["job_title"] == "Официант на смену"


@pytest.mark.asyncio
async def test_apply_shift_conflict(
    client: AsyncClient,
    sample_application: ApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date

    from app.services.application_service import ShiftConflictError

    class DummyWorker:
        id = uuid4()

    conflicting_app = type("App", (), {"id": uuid4()})()
    conflicting_slot = type(
        "Slot",
        (),
        {
            "shift_date": date(2026, 6, 19),
            "start_time": time(10, 0),
            "end_time": time(18, 0),
        },
    )()
    conflicting_app.shift_slot = conflicting_slot
    conflicting_app.job_request = type("Job", (), {"title": "Бармен"})()

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_apply(session, worker, shift_slot_id, *, cancel_conflicting_id=None):
        raise ShiftConflictError(conflicting_app)

    monkeypatch.setattr("app.api.routes.applications.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr("app.api.routes.applications.application_service.apply_to_shift", mock_apply)

    response = await client.post(
        "/api/v1/applications",
        headers=_auth_headers(),
        json={"shift_slot_id": str(uuid4())},
    )
    assert response.status_code == 409
    body = response.json()
    assert "conflicting" in body
    assert body["conflicting"]["job_title"] == "Бармен"


@pytest.mark.asyncio
async def test_cancel_application_success(
    client: AsyncClient,
    sample_application: ApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()

    app_id = sample_application.id

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_cancel(session, worker, application_id):
        assert application_id == app_id
        cancelled = sample_application.model_copy(
            update={"status": ApplicationStatus.cancelled_by_worker}
        )
        return cancelled

    monkeypatch.setattr("app.api.routes.applications.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr("app.api.routes.applications.application_service.cancel_application", mock_cancel)

    response = await client.delete(f"/api/v1/applications/{app_id}", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled_by_worker"


@pytest.mark.asyncio
async def test_list_my_applications(
    client: AsyncClient,
    sample_application: ApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_list(session, worker):
        return ApplicationListResponse(items=[sample_application], total=1)

    monkeypatch.setattr("app.api.routes.applications.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr("app.api.routes.applications.application_service.list_my_applications", mock_list)

    response = await client.get("/api/v1/applications/mine", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_apply_worker_not_found(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_worker(session, user_id):
        return None

    monkeypatch.setattr("app.api.routes.applications.worker_service.get_worker_by_user_id", mock_get_worker)

    response = await client.post(
        "/api/v1/applications",
        headers=_auth_headers(),
        json={"shift_slot_id": str(uuid4())},
    )
    assert response.status_code == 404
