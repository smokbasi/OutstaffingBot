from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models import (
    Gender,
    JobCategory,
    JobRequest,
    JobRequestStatus,
    MetroStation,
    RequiredGender,
    ShiftSlot,
    User,
    UserRole,
    Worker,
    WorkerExperience,
    WorkerPreferences,
)
from app.services.matching_service import (
    _worker_matches_job_age,
    _worker_matches_job_gender,
    _worker_push_category_ids,
    find_workers_for_job,
)


def _make_job(
    *,
    category_id: int = 2,
    hourly_rate: Decimal = Decimal("400"),
    metro_station_id: int = 1,
    status: JobRequestStatus = JobRequestStatus.active,
    notify: bool = True,
) -> JobRequest:
    job = JobRequest(
        id=uuid4(),
        employer_id=uuid4(),
        category_id=category_id,
        title="Официант",
        description="Зал",
        metro_station_id=metro_station_id,
        hourly_rate=hourly_rate,
        workers_needed=1,
        status=status,
        notify_matching_workers=notify,
    )
    job.category = JobCategory(id=category_id, slug="waiter", name_ru="Официант")
    job.metro_station = MetroStation(id=metro_station_id, name="Автово", line_name="Красная")
    job.shift_slots = [
        ShiftSlot(
            id=uuid4(),
            job_request_id=job.id,
            shift_date=date(2026, 7, 1),
            start_time=time(10, 0),
            end_time=time(18, 0),
            slots_total=2,
            slots_filled=0,
        )
    ]
    return job


def _make_worker(
    *,
    category_id: int = 2,
    min_rate: Decimal | None = Decimal("350"),
    notifications_enabled: bool = True,
    metro_station_id: int | None = 1,
    age: int = 25,
    gender: Gender | None = Gender.male,
    preferences: WorkerPreferences | None = None,
) -> Worker:
    user = User(id=uuid4(), telegram_id=1001, role=UserRole.worker, is_blocked=False)
    worker = Worker(
        id=uuid4(),
        user_id=user.id,
        first_name="Иван",
        last_name="Тест",
        age=age,
        gender=gender,
        metro_station_id=metro_station_id,
        min_hourly_rate=min_rate,
        notifications_enabled=notifications_enabled,
        resume_completed=True,
    )
    worker.user = user
    worker.experiences = [
        WorkerExperience(
            id=uuid4(),
            worker_id=worker.id,
            category_id=category_id,
            role_title="Официант",
            duration_months=12,
        )
    ]
    if preferences is not None:
        user.preferences = preferences
    return worker


def test_worker_push_category_ids_uses_experiences_by_default() -> None:
    worker = _make_worker(category_id=2)
    assert _worker_push_category_ids(worker, None) == [2]


def test_worker_push_category_ids_filters_by_preferences() -> None:
    worker = _make_worker(category_id=2)
    worker.experiences.append(
        WorkerExperience(
            id=uuid4(),
            worker_id=worker.id,
            category_id=5,
            role_title="Бармен",
            duration_months=6,
        )
    )
    prefs = WorkerPreferences(user_id=worker.user_id, category_ids=[5])
    assert _worker_push_category_ids(worker, prefs) == [5]


def test_worker_matches_job_gender_and_age() -> None:
    worker = _make_worker(gender=Gender.male, age=25)
    job = _make_job()
    job.required_gender = RequiredGender.female
    assert _worker_matches_job_gender(worker, job) is False
    job.required_gender = RequiredGender.male
    assert _worker_matches_job_gender(worker, job) is True
    job.max_age = 20
    assert _worker_matches_job_age(worker, job) is False


@pytest.mark.asyncio
async def test_find_workers_for_job_matches_by_category_and_rate(db_session) -> None:
    from app.services.matching_service import find_workers_for_job as find_fn

    worker_match = _make_worker(category_id=2, min_rate=Decimal("300"))
    worker_low_rate = _make_worker(category_id=2, min_rate=Decimal("500"))
    worker_other_cat = _make_worker(category_id=5, min_rate=Decimal("300"))
    worker_disabled = _make_worker(category_id=2, notifications_enabled=False)

    job = _make_job(category_id=2, hourly_rate=Decimal("400"))

    class _ScalarsResult:
        def __init__(self, items):
            self._items = items

        def __iter__(self):
            return iter(self._items)

    async def fake_scalars(_stmt):
        return _ScalarsResult(
            [worker_match, worker_low_rate, worker_other_cat, worker_disabled]
        )

    async def fake_same_line(_session, station_id: int):
        return [station_id]

    db_session.scalars = fake_scalars  # type: ignore[method-assign]
    import app.services.matching_service as ms

    original = ms.get_metro_stations_on_same_line
    ms.get_metro_stations_on_same_line = fake_same_line
    try:
        matched = await find_fn(db_session, job)
    finally:
        ms.get_metro_stations_on_same_line = original

    assert len(matched) == 1
    assert matched[0].id == worker_match.id


@pytest.fixture
def db_session():
    class DummySession:
        pass

    return DummySession()
