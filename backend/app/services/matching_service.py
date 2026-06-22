from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Gender,
    Employer,
    JobRequest,
    JobRequestStatus,
    MetroStation,
    RequiredGender,
    ShiftSlot,
    User,
    Worker,
    WorkerPreferences,
)
from app.services import geo_service
from app.schemas.vacancy import VacancyDetail, VacancyFilters, VacancyListItem, VacancyListResponse


@dataclass(frozen=True, slots=True)
class VacancyMatch:
    job: JobRequest
    slot: ShiftSlot


def worker_category_ids(worker: Worker) -> list[int]:
    return list({exp.category_id for exp in worker.experiences})


def effective_category_ids(worker: Worker, filters: VacancyFilters) -> list[int]:
    worker_cats = worker_category_ids(worker)
    if not worker_cats:
        return []
    if filters.category_id is not None:
        return [filters.category_id] if filters.category_id in worker_cats else []
    return worker_cats


def effective_min_rate(worker: Worker, filters: VacancyFilters) -> Decimal:
    if filters.min_hourly_rate is not None:
        return filters.min_hourly_rate
    if worker.min_hourly_rate is not None:
        return worker.min_hourly_rate
    return Decimal(0)


def _gender_filter(worker: Worker):
    if worker.gender is None:
        return or_(
            JobRequest.required_gender.is_(None),
            JobRequest.required_gender == RequiredGender.any,
        )
    gender_map = {
        Gender.male: RequiredGender.male,
        Gender.female: RequiredGender.female,
    }
    mapped = gender_map.get(worker.gender)
    if mapped is None:
        return or_(
            JobRequest.required_gender.is_(None),
            JobRequest.required_gender == RequiredGender.any,
        )
    return or_(
        JobRequest.required_gender.is_(None),
        JobRequest.required_gender == RequiredGender.any,
        JobRequest.required_gender == mapped,
    )


def _effective_city(worker: Worker, filters: VacancyFilters) -> str | None:
    if filters.city is not None:
        return filters.city
    return worker.city or None


def _effective_max_distance_km(worker: Worker, filters: VacancyFilters) -> int | None:
    if filters.max_distance_km is not None:
        return filters.max_distance_km
    if worker.metro_radius_km and worker.metro_radius_km > 0:
        return worker.metro_radius_km
    return None


def _distance_km_between_stations(worker_station: MetroStation | None, job_station: MetroStation | None) -> float | None:
    if worker_station is None or job_station is None:
        return None
    if worker_station.lat is None or worker_station.lon is None:
        return None
    if job_station.lat is None or job_station.lon is None:
        return None
    return geo_service.haversine_km(worker_station.lat, worker_station.lon, job_station.lat, job_station.lon)


def _base_vacancy_conditions(worker: Worker, filters: VacancyFilters, category_ids: list[int]):
    min_rate = effective_min_rate(worker, filters)
    conditions = [
        JobRequest.status == JobRequestStatus.active,
        JobRequest.category_id.in_(category_ids),
        JobRequest.hourly_rate >= min_rate,
        ShiftSlot.slots_filled < ShiftSlot.slots_total,
        ShiftSlot.shift_date >= date.today(),
        worker.age >= func.coalesce(JobRequest.min_age, 16),
        worker.age <= func.coalesce(JobRequest.max_age, 70),
        _gender_filter(worker),
    ]
    if filters.metro_station_id is not None:
        conditions.append(JobRequest.metro_station_id == filters.metro_station_id)
    city = _effective_city(worker, filters)
    if city is not None:
        conditions.append(JobRequest.city == city)
    return conditions


def _available_slots(job: JobRequest) -> int:
    today = date.today()
    total = 0
    for slot in job.shift_slots:
        if slot.shift_date >= today and slot.slots_filled < slot.slots_total:
            total += slot.slots_total - slot.slots_filled
    return total


def _next_shift(job: JobRequest) -> ShiftSlot | None:
    today = date.today()
    available = [
        slot
        for slot in job.shift_slots
        if slot.shift_date >= today and slot.slots_filled < slot.slots_total
    ]
    if not available:
        return None
    return min(available, key=lambda slot: (slot.shift_date, slot.start_time))


def _job_to_list_item(job: JobRequest) -> VacancyListItem:
    next_slot = _next_shift(job)
    return VacancyListItem(
        id=job.id,
        category_id=job.category_id,
        category_name=job.category.name_ru if job.category else None,
        title=job.title,
        metro_station_id=job.metro_station_id,
        metro_station_name=job.metro_station.name if job.metro_station else None,
        hourly_rate=job.hourly_rate,
        workers_needed=job.workers_needed,
        next_shift_date=next_slot.shift_date if next_slot else None,
        next_shift_start=next_slot.start_time if next_slot else None,
        next_shift_end=next_slot.end_time if next_slot else None,
        available_slots=_available_slots(job),
    )


def _job_to_detail(job: JobRequest) -> VacancyDetail:
    shift_slots = sorted(job.shift_slots, key=lambda slot: (slot.shift_date, slot.start_time))
    today = date.today()
    available_slots = [
        slot
        for slot in shift_slots
        if slot.shift_date >= today and slot.slots_filled < slot.slots_total
    ]
    return VacancyDetail(
        id=job.id,
        category_id=job.category_id,
        category_name=job.category.name_ru if job.category else None,
        title=job.title,
        description=job.description,
        metro_station_id=job.metro_station_id,
        metro_station_name=job.metro_station.name if job.metro_station else None,
        address=job.address,
        hourly_rate=job.hourly_rate,
        workers_needed=job.workers_needed,
        min_experience_months=job.min_experience_months,
        dress_code=job.dress_code,
        shift_slots=[
            {
                "id": slot.id,
                "shift_date": slot.shift_date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "slots_total": slot.slots_total,
                "slots_filled": slot.slots_filled,
            }
            for slot in available_slots
        ],
        created_at=job.created_at,
    )


async def find_matching_vacancies(
    session: AsyncSession,
    worker: Worker,
    filters: VacancyFilters,
) -> list[VacancyMatch]:
    category_ids = effective_category_ids(worker, filters)
    if not category_ids:
        return []

    conditions = _base_vacancy_conditions(worker, filters, category_ids)
    stmt = (
        select(JobRequest, ShiftSlot)
        .join(ShiftSlot, JobRequest.id == ShiftSlot.job_request_id)
        .options(selectinload(JobRequest.metro_station))
        .where(*conditions)
        .order_by(ShiftSlot.shift_date, ShiftSlot.start_time)
        .limit(filters.limit * 3)
    )
    rows = (await session.execute(stmt)).all()
    matches = [VacancyMatch(job=row[0], slot=row[1]) for row in rows]

    max_km = _effective_max_distance_km(worker, filters)
    if max_km is None:
        return matches[: filters.limit]

    worker_station = worker.metro_station
    if worker_station is None and worker.metro_station_id is not None:
        worker_station = await session.scalar(
            select(MetroStation).where(MetroStation.id == worker.metro_station_id)
        )

    filtered: list[VacancyMatch] = []
    for match in matches:
        distance = _distance_km_between_stations(worker_station, match.job.metro_station)
        if distance is None or distance <= max_km:
            filtered.append(match)
        if len(filtered) >= filters.limit:
            break
    return filtered


async def list_vacancies_for_worker(
    session: AsyncSession,
    worker: Worker,
    filters: VacancyFilters,
) -> VacancyListResponse:
    category_ids = effective_category_ids(worker, filters)
    if not category_ids:
        return VacancyListResponse(items=[], total=0, page=filters.page, limit=filters.limit)

    conditions = _base_vacancy_conditions(worker, filters, category_ids)
    matched_ids_subq = (
        select(JobRequest.id)
        .join(ShiftSlot, JobRequest.id == ShiftSlot.job_request_id)
        .where(*conditions)
        .group_by(JobRequest.id)
        .subquery()
    )

    total = await session.scalar(select(func.count()).select_from(matched_ids_subq)) or 0
    offset = (filters.page - 1) * filters.limit

    page_ids = list(
        await session.scalars(
            select(JobRequest.id)
            .join(matched_ids_subq, JobRequest.id == matched_ids_subq.c.id)
            .order_by(JobRequest.created_at.desc())
            .offset(offset)
            .limit(filters.limit)
        )
    )

    if not page_ids:
        return VacancyListResponse(items=[], total=total, page=filters.page, limit=filters.limit)

    jobs = list(
        await session.scalars(
            select(JobRequest)
            .options(
                selectinload(JobRequest.shift_slots),
                selectinload(JobRequest.category),
                selectinload(JobRequest.metro_station),
            )
            .where(JobRequest.id.in_(page_ids))
            .order_by(JobRequest.created_at.desc())
        )
    )

    max_km = _effective_max_distance_km(worker, filters)
    if max_km is not None:
        worker_station = worker.metro_station
        if worker_station is None and worker.metro_station_id is not None:
            worker_station = await session.scalar(
                select(MetroStation).where(MetroStation.id == worker.metro_station_id)
            )
        jobs = [
            job
            for job in jobs
            if (
                (d := _distance_km_between_stations(worker_station, job.metro_station)) is None
                or d <= max_km
            )
        ]

    return VacancyListResponse(
        items=[_job_to_list_item(job) for job in jobs],
        total=total,
        page=filters.page,
        limit=filters.limit,
    )


async def get_vacancy_for_worker(
    session: AsyncSession,
    worker: Worker,
    job_id: UUID,
    filters: VacancyFilters | None = None,
) -> VacancyDetail | None:
    filters = filters or VacancyFilters()
    category_ids = effective_category_ids(worker, filters)
    if not category_ids:
        return None

    conditions = _base_vacancy_conditions(worker, filters, category_ids)
    conditions.append(JobRequest.id == job_id)

    matched_id = await session.scalar(
        select(JobRequest.id)
        .join(ShiftSlot, JobRequest.id == ShiftSlot.job_request_id)
        .where(*conditions)
        .limit(1)
    )
    if matched_id is None:
        return None

    job = await session.scalar(
        select(JobRequest)
        .options(
            selectinload(JobRequest.shift_slots),
            selectinload(JobRequest.category),
            selectinload(JobRequest.metro_station),
        )
        .where(JobRequest.id == matched_id)
    )
    if job is None:
        return None
    return _job_to_detail(job)


async def get_metro_stations_on_same_line(
    session: AsyncSession,
    station_id: int,
) -> list[int]:
    station = await session.scalar(select(MetroStation).where(MetroStation.id == station_id))
    if station is None:
        return [station_id]
    result = await session.scalars(
        select(MetroStation.id).where(
            MetroStation.line_name == station.line_name,
            MetroStation.is_active.is_(True),
        )
    )
    return list(result.all())


def _worker_effective_min_rate(worker: Worker, preferences: WorkerPreferences | None) -> Decimal:
    if preferences is not None and preferences.min_hourly_rate is not None:
        return preferences.min_hourly_rate
    if worker.min_hourly_rate is not None:
        return worker.min_hourly_rate
    return Decimal(0)


def _worker_push_category_ids(worker: Worker, preferences: WorkerPreferences | None) -> list[int]:
    experience_ids = worker_category_ids(worker)
    if not experience_ids:
        return []
    if preferences is not None and preferences.category_ids:
        return [cat_id for cat_id in preferences.category_ids if cat_id in experience_ids]
    return experience_ids


def _worker_matches_job_gender(worker: Worker, job: JobRequest) -> bool:
    if job.required_gender is None or job.required_gender == RequiredGender.any:
        return True
    if worker.gender is None:
        return True
    gender_map = {
        Gender.male: RequiredGender.male,
        Gender.female: RequiredGender.female,
    }
    mapped = gender_map.get(worker.gender)
    if mapped is None:
        return True
    return job.required_gender == mapped


def _worker_matches_job_age(worker: Worker, job: JobRequest) -> bool:
    min_age = job.min_age if job.min_age is not None else 16
    max_age = job.max_age if job.max_age is not None else 70
    return min_age <= worker.age <= max_age


async def _worker_matches_job_metro(
    session: AsyncSession,
    worker: Worker,
    preferences: WorkerPreferences | None,
    job: JobRequest,
) -> bool:
    if preferences is not None and preferences.metro_station_ids:
        preferred_ids = set(preferences.metro_station_ids)
        if job.metro_station_id in preferred_ids:
            return True
        for station_id in preferences.metro_station_ids:
            same_line = await get_metro_stations_on_same_line(session, station_id)
            if job.metro_station_id in same_line:
                return True
        return False
    return True


def _job_has_available_slots(job: JobRequest) -> bool:
    today = date.today()
    return any(
        slot.shift_date >= today and slot.slots_filled < slot.slots_total for slot in job.shift_slots
    )


async def find_active_jobs_for_worker(session: AsyncSession, worker: Worker) -> list[JobRequest]:
    """Active jobs matching a newly registered worker (employer push)."""
    category_ids = worker_category_ids(worker)
    if not category_ids:
        return []

    stmt = (
        select(JobRequest)
        .options(
            selectinload(JobRequest.shift_slots),
            selectinload(JobRequest.category),
            selectinload(JobRequest.metro_station),
            selectinload(JobRequest.employer).selectinload(Employer.user),
        )
        .where(
            JobRequest.status == JobRequestStatus.active,
            JobRequest.notify_matching_workers.is_(True),
            JobRequest.category_id.in_(category_ids),
        )
    )
    jobs = list(await session.scalars(stmt))
    matched: list[JobRequest] = []
    for job in jobs:
        if not _job_has_available_slots(job):
            continue
        if job.hourly_rate < _worker_effective_min_rate(worker, None):
            continue
        if not _worker_matches_job_gender(worker, job):
            continue
        if not _worker_matches_job_age(worker, job):
            continue
        if worker.city and job.city and worker.city != job.city:
            continue
        matched.append(job)
    return matched


async def find_workers_for_job(session: AsyncSession, job: JobRequest) -> list[Worker]:
    if job.status != JobRequestStatus.active or not job.notify_matching_workers:
        return []
    if not _job_has_available_slots(job):
        return []

    stmt = (
        select(Worker)
        .join(User, Worker.user_id == User.id)
        .outerjoin(WorkerPreferences, WorkerPreferences.user_id == User.id)
        .options(
            selectinload(Worker.experiences),
            selectinload(Worker.user).selectinload(User.preferences),
            selectinload(Worker.metro_station),
        )
        .where(
            User.is_blocked.is_(False),
            Worker.notifications_enabled.is_(True),
            or_(WorkerPreferences.push_enabled.is_(True), WorkerPreferences.id.is_(None)),
        )
    )
    workers = list(await session.scalars(stmt))

    matched: list[Worker] = []
    for worker in workers:
        if not worker.notifications_enabled:
            continue
        preferences = worker.user.preferences if worker.user else None
        category_ids = _worker_push_category_ids(worker, preferences)
        if job.category_id not in category_ids:
            continue
        if job.hourly_rate < _worker_effective_min_rate(worker, preferences):
            continue
        if not _worker_matches_job_gender(worker, job):
            continue
        if not _worker_matches_job_age(worker, job):
            continue
        if not await _worker_matches_job_metro(session, worker, preferences, job):
            continue
        matched.append(worker)
    return matched
