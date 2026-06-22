from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_employer, get_current_user
from app.db.models import ApplicationStatus, Employer, User, UserRole, VerificationStatus
from app.db.session import get_db_session
from app.main import app
from app.schemas.application import EmployerApplicationListResponse, EmployerApplicationRead
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
def sample_employer_application() -> EmployerApplicationRead:
    return EmployerApplicationRead(
        id=uuid4(),
        job_request_id=uuid4(),
        shift_slot_id=uuid4(),
        status=ApplicationStatus.pending,
        applied_at=datetime.now(timezone.utc),
        shift_date=date(2026, 6, 25),
        start_time=time(10, 0),
        end_time=time(22, 0),
        worker_id=uuid4(),
        worker_first_name="Пётр",
        worker_last_name="Иванов",
        worker_age=25,
        worker_experience_months=12,
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


@pytest.mark.asyncio
async def test_list_job_applications_success(
    client: AsyncClient,
    test_employer: Employer,
    sample_employer_application: EmployerApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = sample_employer_application.job_request_id

    async def mock_list(session, employer_id, job_id_arg):
        assert employer_id == test_employer.id
        assert job_id_arg == job_id
        return EmployerApplicationListResponse(items=[sample_employer_application], total=1)

    monkeypatch.setattr(
        "app.api.routes.employer.application_service.list_job_applications",
        mock_list,
    )

    response = await client.get(
        f"/api/v1/employer/jobs/{job_id}/applications",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["worker_first_name"] == "Пётр"
    assert data["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_job_applications_not_found(
    client: AsyncClient,
    test_employer: Employer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.application_service import JobNotFoundForEmployerError

    job_id = uuid4()

    async def mock_list(session, employer_id, job_id_arg):
        raise JobNotFoundForEmployerError()

    monkeypatch.setattr(
        "app.api.routes.employer.application_service.list_job_applications",
        mock_list,
    )

    response = await client.get(
        f"/api/v1/employer/jobs/{job_id}/applications",
        headers=_auth_headers(),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_application_accept(
    client: AsyncClient,
    test_employer: Employer,
    sample_employer_application: EmployerApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_id = sample_employer_application.id
    accepted = sample_employer_application.model_copy(update={"status": ApplicationStatus.accepted})

    async def mock_update(session, employer_id, application_id, status, **kwargs):
        assert employer_id == test_employer.id
        assert application_id == app_id
        assert status == ApplicationStatus.accepted
        return accepted

    monkeypatch.setattr(
        "app.api.routes.employer.application_service.update_application_by_employer",
        mock_update,
    )

    response = await client.patch(
        f"/api/v1/employer/applications/{app_id}",
        headers=_auth_headers(),
        json={"status": "accepted"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_patch_application_reject(
    client: AsyncClient,
    test_employer: Employer,
    sample_employer_application: EmployerApplicationRead,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_id = sample_employer_application.id
    rejected = sample_employer_application.model_copy(update={"status": ApplicationStatus.rejected})

    async def mock_update(session, employer_id, application_id, status, **kwargs):
        assert status == ApplicationStatus.rejected
        return rejected

    monkeypatch.setattr(
        "app.api.routes.employer.application_service.update_application_by_employer",
        mock_update,
    )

    response = await client.patch(
        f"/api/v1/employer/applications/{app_id}",
        headers=_auth_headers(),
        json={"status": "rejected"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_patch_application_invalid_status(
    client: AsyncClient,
    sample_employer_application: EmployerApplicationRead,
) -> None:
    response = await client.patch(
        f"/api/v1/employer/applications/{sample_employer_application.id}",
        headers=_auth_headers(),
        json={"status": "pending"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_application_not_pending(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.application_service import ApplicationNotPendingError

    app_id = uuid4()

    async def mock_update(session, employer_id, application_id, status, **kwargs):
        raise ApplicationNotPendingError()

    monkeypatch.setattr(
        "app.api.routes.employer.application_service.update_application_by_employer",
        mock_update,
    )

    response = await client.patch(
        f"/api/v1/employer/applications/{app_id}",
        headers=_auth_headers(),
        json={"status": "accepted"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_patch_application_not_found(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.application_service import ApplicationNotFoundError

    app_id = uuid4()

    async def mock_update(session, employer_id, application_id, status, **kwargs):
        raise ApplicationNotFoundError("Application not found")

    monkeypatch.setattr(
        "app.api.routes.employer.application_service.update_application_by_employer",
        mock_update,
    )

    response = await client.patch(
        f"/api/v1/employer/applications/{app_id}",
        headers=_auth_headers(),
        json={"status": "accepted"},
    )
    assert response.status_code == 404
