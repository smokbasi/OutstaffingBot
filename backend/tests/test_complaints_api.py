from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_employer, get_current_user
from app.db.models import (
    ApplicationStatus,
    ComplaintStatus,
    ComplaintViolationType,
    Employer,
    JobRequestStatus,
    User,
    UserRole,
)
from app.db.session import get_db_session
from app.main import app
from app.schemas.complaint import (
    ComplaintRead,
    EmployerComplaintApplicationsResponse,
    EmployerComplaintJobRead,
    EmployerComplaintJobsResponse,
    WorkerComplaintContextResponse,
    WorkerEligibleApplicationRead,
)
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
WORKER_TELEGRAM_ID = 12345
EMPLOYER_TELEGRAM_ID = 54321


@pytest.fixture
def worker_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=WORKER_TELEGRAM_ID,
        username="worker1",
        role=UserRole.worker,
    )


@pytest.fixture
def employer_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=EMPLOYER_TELEGRAM_ID,
        username="employer1",
        role=UserRole.employer,
    )


@pytest.fixture
def test_employer(employer_user: User) -> Employer:
    return Employer(
        id=uuid4(),
        user_id=employer_user.id,
        company_name="ООО Тест",
        contact_phone="+79990001122",
        contact_person="Иван Руководитель",
        verified=True,
    )


def _auth_headers(telegram_id: int) -> dict[str, str]:
    return {"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, telegram_id)}"}


@pytest.fixture
async def worker_client(worker_user: User, monkeypatch: pytest.MonkeyPatch):
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()

    async def override_user():
        return worker_user

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


@pytest.fixture
async def employer_client(
    employer_user: User,
    test_employer: Employer,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()

    async def override_user():
        return employer_user

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


def _sample_worker_context() -> WorkerComplaintContextResponse:
    application_id = uuid4()
    return WorkerComplaintContextResponse(
        applications=[
            WorkerEligibleApplicationRead(
                id=application_id,
                job_request_id=uuid4(),
                shift_slot_id=uuid4(),
                status=ApplicationStatus.accepted,
                job_title="Официант на смену",
                company_name="ООО Тест",
                shift_date=date(2026, 6, 25),
                start_time=time(10, 0),
                end_time=time(22, 0),
            )
        ]
    )


def _sample_complaint(application_id=None) -> ComplaintRead:
    return ComplaintRead(
        id=uuid4(),
        application_id=application_id or uuid4(),
        job_request_id=uuid4(),
        shift_slot_id=uuid4(),
        violation_type=ComplaintViolationType.late,
        description="Работодатель опоздал более чем на час.",
        status=ComplaintStatus.open,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_worker_my_context_includes_company_name(
    worker_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()

    context = _sample_worker_context()

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_context(session, worker):
        return context

    monkeypatch.setattr(
        "app.api.routes.complaints.worker_service.get_worker_by_user_id",
        mock_get_worker,
    )
    monkeypatch.setattr(
        "app.api.routes.complaints.complaint_service.get_worker_complaint_context",
        mock_context,
    )

    response = await worker_client.get(
        "/api/v1/complaints/my-context",
        headers=_auth_headers(WORKER_TELEGRAM_ID),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["applications"]) == 1
    assert data["applications"][0]["company_name"] == "ООО Тест"


@pytest.mark.asyncio
async def test_worker_create_complaint_success(
    worker_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()

    application_id = uuid4()
    complaint = _sample_complaint(application_id).model_copy(
        update={"violation_type": ComplaintViolationType.no_payment}
    )

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_create(session, worker, *, application_id, violation_type, description):
        assert violation_type == ComplaintViolationType.no_payment
        return complaint

    monkeypatch.setattr(
        "app.api.routes.complaints.worker_service.get_worker_by_user_id",
        mock_get_worker,
    )
    monkeypatch.setattr(
        "app.api.routes.complaints.complaint_service.create_worker_complaint",
        mock_create,
    )

    response = await worker_client.post(
        "/api/v1/complaints",
        headers=_auth_headers(WORKER_TELEGRAM_ID),
        json={
            "application_id": str(application_id),
            "violation_type": "no_payment",
            "description": "Оплата за смену так и не поступила.",
        },
    )
    assert response.status_code == 201
    assert response.json()["violation_type"] == "no_payment"


@pytest.mark.asyncio
async def test_worker_create_complaint_forbidden_other_application(
    worker_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import complaint_service

    class DummyWorker:
        id = uuid4()

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_create(session, worker, *, application_id, violation_type, description):
        raise complaint_service.ComplaintNotFoundError("Отклик не найден.")

    monkeypatch.setattr(
        "app.api.routes.complaints.worker_service.get_worker_by_user_id",
        mock_get_worker,
    )
    monkeypatch.setattr(
        "app.api.routes.complaints.complaint_service.create_worker_complaint",
        mock_create,
    )

    response = await worker_client.post(
        "/api/v1/complaints",
        headers=_auth_headers(WORKER_TELEGRAM_ID),
        json={
            "application_id": str(uuid4()),
            "violation_type": "late",
            "description": "Работодатель опоздал более чем на час.",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_worker_create_complaint_with_stop_words_returns_201(
    worker_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()

    application_id = uuid4()
    profane_description = "Это описание содержит заведомо запрещённое слово хуйня."
    complaint = _sample_complaint(application_id).model_copy(
        update={
            "description": profane_description,
            "violation_type": ComplaintViolationType.no_payment,
        }
    )
    moderation_called: list[str] = []

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_create(session, worker, *, application_id, violation_type, description):
        moderation_called.append(description)
        return complaint

    async def mock_record(*args, **kwargs):
        moderation_called.append("record")

    monkeypatch.setattr(
        "app.api.routes.complaints.worker_service.get_worker_by_user_id",
        mock_get_worker,
    )
    monkeypatch.setattr(
        "app.api.routes.complaints.complaint_service.create_worker_complaint",
        mock_create,
    )
    monkeypatch.setattr(
        "app.services.moderation_violation_service.record_content_rejection",
        mock_record,
    )

    response = await worker_client.post(
        "/api/v1/complaints",
        headers=_auth_headers(WORKER_TELEGRAM_ID),
        json={
            "application_id": str(application_id),
            "violation_type": "no_payment",
            "description": profane_description,
        },
    )
    assert response.status_code == 201
    assert response.json()["description"] == profane_description
    assert "record" not in moderation_called


@pytest.mark.asyncio
async def test_employer_list_complaint_jobs(
    employer_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = uuid4()
    jobs = EmployerComplaintJobsResponse(
        items=[
            EmployerComplaintJobRead(
                id=job_id,
                title="Официант на смену",
                status=JobRequestStatus.active,
                applications_count=2,
            )
        ]
    )

    async def mock_list_jobs(session, employer):
        return jobs

    monkeypatch.setattr(
        "app.api.routes.employer.complaint_service.list_employer_complaint_jobs",
        mock_list_jobs,
    )

    response = await employer_client.get(
        "/api/v1/employer/complaints/jobs",
        headers=_auth_headers(EMPLOYER_TELEGRAM_ID),
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["applications_count"] == 2


@pytest.mark.asyncio
async def test_employer_list_complaint_applications(
    employer_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = uuid4()
    applications = EmployerComplaintApplicationsResponse(items=[], total=0)

    async def mock_list_apps(session, employer, job_id_arg):
        assert job_id_arg == job_id
        return applications

    monkeypatch.setattr(
        "app.api.routes.employer.complaint_service.list_employer_complaint_applications",
        mock_list_apps,
    )

    response = await employer_client.get(
        f"/api/v1/employer/complaints/jobs/{job_id}/applications",
        headers=_auth_headers(EMPLOYER_TELEGRAM_ID),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_employer_create_complaint_success(
    employer_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_id = uuid4()
    complaint = _sample_complaint(application_id).model_copy(
        update={"violation_type": ComplaintViolationType.no_show, "description": None}
    )

    async def mock_create(session, employer, *, application_id, violation_type, description):
        assert description is None
        return complaint

    monkeypatch.setattr(
        "app.api.routes.employer.complaint_service.create_employer_complaint",
        mock_create,
    )

    response = await employer_client.post(
        "/api/v1/employer/complaints",
        headers=_auth_headers(EMPLOYER_TELEGRAM_ID),
        json={
            "application_id": str(application_id),
            "violation_type": "no_show",
        },
    )
    assert response.status_code == 201
    assert response.json()["violation_type"] == "no_show"


@pytest.mark.asyncio
async def test_employer_create_complaint_forbidden_other_job(
    employer_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import complaint_service

    async def mock_create(session, employer, *, application_id, violation_type, description):
        raise complaint_service.ComplaintNotFoundError("Отклик не найден.")

    monkeypatch.setattr(
        "app.api.routes.employer.complaint_service.create_employer_complaint",
        mock_create,
    )

    response = await employer_client.post(
        "/api/v1/employer/complaints",
        headers=_auth_headers(EMPLOYER_TELEGRAM_ID),
        json={
            "application_id": str(uuid4()),
            "violation_type": "no_show",
        },
    )
    assert response.status_code == 404
