from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.models import Gender, User, UserRole
from app.db.session import get_db_session
from app.main import app
from app.schemas.vacancy import VacancyDetail, VacancyListItem, VacancyListResponse
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
def sample_vacancy_list() -> VacancyListResponse:
    job_id = uuid4()
    return VacancyListResponse(
        items=[
            VacancyListItem(
                id=job_id,
                category_id=2,
                category_name="Официант",
                title="Официант на смену",
                metro_station_id=1,
                metro_station_name="Автово",
                hourly_rate=Decimal("400.00"),
                workers_needed=2,
                next_shift_date=date(2026, 6, 25),
                next_shift_start=time(10, 0),
                next_shift_end=time(22, 0),
                available_slots=2,
                includes_lunch=True,
                is_matched=True,
            )
        ],
        total=1,
        page=1,
        limit=20,
    )


@pytest.fixture
def sample_vacancy_detail(sample_vacancy_list: VacancyListResponse) -> VacancyDetail:
    item = sample_vacancy_list.items[0]
    return VacancyDetail(
        id=item.id,
        category_id=item.category_id,
        category_name=item.category_name,
        title=item.title,
        description="Обслуживание зала",
        metro_station_id=item.metro_station_id,
        metro_station_name=item.metro_station_name,
        address="ул. Примерная, 1",
        hourly_rate=item.hourly_rate,
        workers_needed=item.workers_needed,
        min_experience_months=6,
        dress_code="Чёрная форма",
        includes_lunch=True,
        shift_slots=[
            {
                "id": uuid4(),
                "shift_date": date(2026, 6, 25),
                "start_time": time(10, 0),
                "end_time": time(22, 0),
                "slots_total": 2,
                "slots_filled": 0,
            }
        ],
        created_at=datetime.now(timezone.utc),
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
async def test_list_vacancies_success(
    client: AsyncClient,
    sample_vacancy_list: VacancyListResponse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()
        age = 25
        gender = Gender.male
        min_hourly_rate = Decimal("350")
        metro_station_id = 1
        metro_radius_km = 0
        experiences = []

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_list(session, worker, filters):
        assert filters.page == 1
        assert filters.limit == 20
        return sample_vacancy_list

    monkeypatch.setattr("app.api.routes.worker_vacancies.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr(
        "app.api.routes.worker_vacancies.matching_service.list_vacancies_for_worker",
        mock_list,
    )

    response = await client.get("/api/v1/worker/vacancies", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["category_name"] == "Официант"
    assert data["items"][0]["includes_lunch"] is True


@pytest.mark.asyncio
async def test_get_vacancy_detail_includes_lunch_when_set(
    client: AsyncClient,
    sample_vacancy_detail: VacancyDetail,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()
        age = 25
        gender = Gender.male
        min_hourly_rate = Decimal("350")
        metro_station_id = 1
        metro_radius_km = 0
        experiences = []

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_get(session, worker, job_id, filters=None):
        return sample_vacancy_detail if job_id == sample_vacancy_detail.id else None

    monkeypatch.setattr("app.api.routes.worker_vacancies.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr(
        "app.api.routes.worker_vacancies.matching_service.get_vacancy_for_worker",
        mock_get,
    )

    response = await client.get(
        f"/api/v1/worker/vacancies/{sample_vacancy_detail.id}",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["includes_lunch"] is True


@pytest.mark.asyncio
async def test_list_vacancies_with_filters(
    client: AsyncClient,
    sample_vacancy_list: VacancyListResponse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()
        age = 25
        gender = Gender.male
        min_hourly_rate = Decimal("350")
        metro_station_id = 1
        metro_radius_km = 0
        experiences = []

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_list(session, worker, filters):
        assert filters.category_id == 2
        assert filters.metro_station_id == 1
        assert filters.min_hourly_rate == Decimal("400")
        return sample_vacancy_list

    monkeypatch.setattr("app.api.routes.worker_vacancies.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr(
        "app.api.routes.worker_vacancies.matching_service.list_vacancies_for_worker",
        mock_list,
    )

    response = await client.get(
        "/api/v1/worker/vacancies?category_id=2&metro_station_id=1&min_hourly_rate=400&page=2&limit=10",
        headers=_auth_headers(),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_vacancies_worker_not_found(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_worker(session, user_id):
        return None

    monkeypatch.setattr("app.api.routes.worker_vacancies.worker_service.get_worker_by_user_id", mock_get_worker)
    response = await client.get("/api/v1/worker/vacancies", headers=_auth_headers())
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_vacancy_detail_success(
    client: AsyncClient,
    sample_vacancy_detail: VacancyDetail,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWorker:
        id = uuid4()
        age = 25
        gender = Gender.male
        min_hourly_rate = Decimal("350")
        metro_station_id = 1
        metro_radius_km = 0
        experiences = []

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_get(session, worker, job_id, filters=None):
        return sample_vacancy_detail if job_id == sample_vacancy_detail.id else None

    monkeypatch.setattr("app.api.routes.worker_vacancies.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr(
        "app.api.routes.worker_vacancies.matching_service.get_vacancy_for_worker",
        mock_get,
    )

    response = await client.get(
        f"/api/v1/worker/vacancies/{sample_vacancy_detail.id}",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Официант на смену"
    assert len(data["shift_slots"]) == 1


@pytest.mark.asyncio
async def test_get_vacancy_not_found(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyWorker:
        id = uuid4()
        age = 25
        gender = Gender.male
        min_hourly_rate = Decimal("350")
        metro_station_id = 1
        metro_radius_km = 0
        experiences = []

    async def mock_get_worker(session, user_id):
        return DummyWorker()

    async def mock_get(session, worker, job_id, filters=None):
        return None

    monkeypatch.setattr("app.api.routes.worker_vacancies.worker_service.get_worker_by_user_id", mock_get_worker)
    monkeypatch.setattr(
        "app.api.routes.worker_vacancies.matching_service.get_vacancy_for_worker",
        mock_get,
    )

    response = await client.get(f"/api/v1/worker/vacancies/{uuid4()}", headers=_auth_headers())
    assert response.status_code == 404
