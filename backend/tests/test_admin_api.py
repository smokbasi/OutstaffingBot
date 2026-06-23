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
        class DummySession:
            async def commit(self) -> None:
                return None

        yield DummySession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_session

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


@pytest.mark.asyncio
async def test_admin_list_pending_workers(monkeypatch, admin_client: AsyncClient):
    from datetime import datetime, timezone

    from app.schemas.admin import PendingWorkerRead

    worker_id = uuid4()

    async def fake_list(session):
        return [
            PendingWorkerRead(
                id=worker_id,
                first_name="Иван",
                last_name="Иванов",
                age=25,
                metro_station_name="Автово",
                categories=["Официант"],
                telegram_id=12345,
                username="ivan",
                created_at=datetime(2026, 6, 22, tzinfo=timezone.utc),
            )
        ]

    monkeypatch.setattr(admin_service, "list_pending_workers", fake_list)

    response = await admin_client.get("/api/v1/admin/workers/pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["first_name"] == "Иван"
    assert data[0]["categories"] == ["Официант"]


@pytest.mark.asyncio
async def test_admin_verify_worker_endpoint(monkeypatch, admin_client: AsyncClient):
    worker_id = uuid4()

    class FakeWorker:
        id = worker_id
        first_name = "Иван"
        last_name = "Иванов"

    async def fake_verify(session, wid, *, actor_id, approve):
        assert wid == worker_id
        assert approve is True
        return FakeWorker()

    async def fake_commit(session):
        pass

    monkeypatch.setattr(admin_service, "verify_worker", fake_verify)

    response = await admin_client.post(f"/api/v1/admin/workers/{worker_id}/verify")
    assert response.status_code == 200
    assert response.json()["status"] == "verified"


@pytest.mark.asyncio
async def test_admin_reject_worker_endpoint(monkeypatch, admin_client: AsyncClient):
    worker_id = uuid4()

    class FakeWorker:
        id = worker_id

    async def fake_verify(session, wid, *, actor_id, approve):
        assert approve is False
        return FakeWorker()

    monkeypatch.setattr(admin_service, "verify_worker", fake_verify)

    response = await admin_client.post(f"/api/v1/admin/workers/{worker_id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_admin_list_workers(monkeypatch, admin_client: AsyncClient):
    from datetime import datetime, timezone

    from app.db.models import VerificationStatus
    from app.schemas.admin import AdminWorkerRead

    worker_id = uuid4()

    async def fake_list(session, limit=50):
        assert limit == 50
        return [
            AdminWorkerRead(
                id=worker_id,
                first_name="Пётр",
                last_name="Петров",
                phone="+79991234567",
                verification_status=VerificationStatus.verified,
                telegram_id=54321,
                username="petr",
                created_at=datetime(2026, 6, 22, tzinfo=timezone.utc),
            )
        ]

    monkeypatch.setattr(admin_service, "list_workers", fake_list)

    response = await admin_client.get("/api/v1/admin/workers?limit=50")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["first_name"] == "Пётр"
    assert data[0]["verification_status"] == "verified"


@pytest.mark.asyncio
async def test_admin_list_employers(monkeypatch, admin_client: AsyncClient):
    from datetime import datetime, timezone

    from app.db.models import VerificationStatus
    from app.schemas.admin import AdminEmployerRead

    employer_id = uuid4()

    async def fake_list(session, limit=50):
        return [
            AdminEmployerRead(
                id=employer_id,
                company_name="Кафе Уют",
                verification_status=VerificationStatus.pending,
                contact_person="Анна",
                contact_phone="+79990001122",
                telegram_id=11111,
                username="anna",
                created_at=datetime(2026, 6, 22, tzinfo=timezone.utc),
            )
        ]

    monkeypatch.setattr(admin_service, "list_employers", fake_list)

    response = await admin_client.get("/api/v1/admin/employers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["company_name"] == "Кафе Уют"


@pytest.mark.asyncio
async def test_admin_list_jobs(monkeypatch, admin_client: AsyncClient):
    from datetime import datetime, timezone

    from app.db.models import JobRequestStatus
    from app.schemas.admin import AdminJobRead

    job_id = uuid4()

    async def fake_list(session, limit=50):
        return [
            AdminJobRead(
                id=job_id,
                title="Официант на смену",
                status=JobRequestStatus.active,
                employer_company_name="Кафе Уют",
                created_at=datetime(2026, 6, 22, tzinfo=timezone.utc),
            )
        ]

    monkeypatch.setattr(admin_service, "list_jobs", fake_list)

    response = await admin_client.get("/api/v1/admin/jobs?limit=50")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Официант на смену"
    assert data[0]["status"] == "active"


def test_worker_verification_migration_chain():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert "004_worker_verification" in heads

    rev = script.get_revision("004_worker_verification")
    assert rev.down_revision == "003_phase_9_10"
