from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_employer, get_current_user
from app.db.models import Employer, JobRequestStatus, User, UserRole, VerificationStatus
from app.db.session import get_db_session
from app.main import app
from app.schemas.job_request import JobRequestRead, ShiftSlotRead
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=54321,
        username="employer1",
        role=UserRole.employer,
    )


@pytest.fixture
def test_employer(test_user: User) -> Employer:
    return Employer(
        id=uuid4(),
        user_id=test_user.id,
        company_name="ООО Тест",
        contact_phone="+79990001122",
        contact_person="Иван Руководитель",
        verification_status=VerificationStatus.pending,
    )


@pytest.fixture
def sample_job(test_employer: Employer) -> JobRequestRead:
    slot_id = uuid4()
    now = datetime.now(timezone.utc)
    return JobRequestRead(
        id=uuid4(),
        category_id=1,
        category_name="Официант",
        title="Официант на смену",
        description="Обслуживание зала",
        metro_station_id=1,
        metro_station_name="Автово",
        address="ул. Примерная, 1",
        hourly_rate=Decimal("400.00"),
        workers_needed=2,
        min_experience_months=6,
        required_gender=None,
        min_age=None,
        max_age=None,
        dress_code=None,
        contact_info=None,
        status=JobRequestStatus.draft,
        post_to_groups=False,
        notify_matching_workers=True,
        shift_slots=[
            ShiftSlotRead(
                id=slot_id,
                shift_date=date(2026, 6, 25),
                start_time=time(10, 0),
                end_time=time(22, 0),
                slots_total=2,
                slots_filled=0,
            )
        ],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
async def client(test_user: User, test_employer: Employer, monkeypatch: pytest.MonkeyPatch):
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()

    async def override_user():
        return test_user

    async def override_employer():
        return test_employer

    async def override_session():
        class DummySession:
            async def commit(self) -> None:
                return None

        yield DummySession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_employer] = override_employer
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    app.dependency_overrides.clear()
    config.get_settings.cache_clear()


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 54321)}"}


def _job_payload() -> dict:
    return {
        "category_id": 1,
        "title": "Официант на смену",
        "description": "Обслуживание зала",
        "metro_station_id": 1,
        "hourly_rate": "400.00",
        "workers_needed": 2,
        "shift_slots": [
            {
                "shift_date": "2026-06-25",
                "start_time": "10:00:00",
                "end_time": "22:00:00",
            }
        ],
    }


@pytest.mark.asyncio
async def test_create_job_draft(
    client: AsyncClient,
    sample_job: JobRequestRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_create(session, employer_id, data, **kwargs):
        assert data.title == "Официант на смену"
        return sample_job

    monkeypatch.setattr("app.api.routes.employer.job_service.create_job_request", mock_create)
    response = await client.post("/api/v1/employer/jobs", headers=_auth_headers(), json=_job_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["title"] == "Официант на смену"
    assert len(data["shift_slots"]) == 1


@pytest.mark.asyncio
async def test_list_jobs(
    client: AsyncClient,
    sample_job: JobRequestRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_list(session, employer_id):
        return [sample_job]

    monkeypatch.setattr("app.api.routes.employer.job_service.list_job_requests", mock_list)
    response = await client.get("/api/v1/employer/jobs", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_job.id)


@pytest.mark.asyncio
async def test_get_job_success(
    client: AsyncClient,
    sample_job: JobRequestRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_get(session, employer_id, job_id):
        return sample_job if job_id == sample_job.id else None

    monkeypatch.setattr("app.api.routes.employer.job_service.get_job_request", mock_get)
    response = await client.get(f"/api/v1/employer/jobs/{sample_job.id}", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["title"] == "Официант на смену"


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get(session, employer_id, job_id):
        return None

    monkeypatch.setattr("app.api.routes.employer.job_service.get_job_request", mock_get)
    response = await client.get(f"/api/v1/employer/jobs/{uuid4()}", headers=_auth_headers())
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_job_status_active(
    client: AsyncClient,
    sample_job: JobRequestRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_job = sample_job.model_copy(update={"status": JobRequestStatus.active})

    async def mock_update(session, employer_id, job_id, data, **kwargs):
        assert data.status == JobRequestStatus.active
        return active_job

    monkeypatch.setattr("app.api.routes.employer.job_service.update_job_request", mock_update)
    response = await client.patch(
        f"/api/v1/employer/jobs/{sample_job.id}",
        headers=_auth_headers(),
        json={"status": "active"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_patch_job_invalid_transition(
    client: AsyncClient,
    sample_job: JobRequestRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_update(session, employer_id, job_id, data, **kwargs):
        raise ValueError("Cannot transition from draft to filled")

    monkeypatch.setattr("app.api.routes.employer.job_service.update_job_request", mock_update)
    response = await client.patch(
        f"/api/v1/employer/jobs/{sample_job.id}",
        headers=_auth_headers(),
        json={"status": "filled"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_employer_jobs_require_employer_profile(
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()

    async def mock_get_employer_by_user_id(session, user_id):
        return None

    monkeypatch.setattr(
        "app.services.employer_service.get_employer_by_user_id",
        mock_get_employer_by_user_id,
    )

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
        response = await http_client.post(
            "/api/v1/employer/jobs",
            headers=_auth_headers(),
            json=_job_payload(),
        )

    app.dependency_overrides.clear()
    config.get_settings.cache_clear()
    assert response.status_code == 404
