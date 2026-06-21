from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import JobCategory, MetroStation, User, Worker, WorkerExperience
from app.schemas.worker import WorkerExperienceCreate, WorkerProfileRead, WorkerProfileUpdate
from app.reference.job_categories import sort_job_categories
from app.reference.spb_metro import sort_stations_on_line


async def get_worker_by_user_id(session: AsyncSession, user_id: UUID) -> Worker | None:
    stmt = (
        select(Worker)
        .options(
            selectinload(Worker.experiences).selectinload(WorkerExperience.category),
            selectinload(Worker.metro_station),
        )
        .where(Worker.user_id == user_id)
    )
    return await session.scalar(stmt)


async def get_worker_profile(session: AsyncSession, user: User) -> WorkerProfileRead | None:
    worker = await get_worker_by_user_id(session, user.id)
    if worker is None:
        return None
    return _worker_to_profile(worker)


def _worker_to_profile(worker: Worker) -> WorkerProfileRead:
    experiences = [
        {
            "id": exp.id,
            "category_id": exp.category_id,
            "category_name": exp.category.name_ru if exp.category else "",
            "role_title": exp.role_title,
            "duration_months": exp.duration_months,
            "description": exp.description,
        }
        for exp in worker.experiences
    ]
    return WorkerProfileRead(
        id=worker.id,
        first_name=worker.first_name,
        last_name=worker.last_name,
        age=worker.age,
        gender=worker.gender,
        metro_station_id=worker.metro_station_id,
        metro_station_name=worker.metro_station.name if worker.metro_station else None,
        min_hourly_rate=worker.min_hourly_rate,
        resume_completed=worker.resume_completed,
        experiences=experiences,
    )


async def upsert_worker_profile(
    session: AsyncSession,
    user: User,
    data: WorkerProfileUpdate,
    *,
    resume_completed: bool | None = None,
) -> WorkerProfileRead:
    worker = await get_worker_by_user_id(session, user.id)
    if worker is None:
        worker = Worker(user_id=user.id, first_name=data.first_name, last_name=data.last_name, age=data.age)
        session.add(worker)
    else:
        worker.first_name = data.first_name
        worker.last_name = data.last_name
        worker.age = data.age

    worker.gender = data.gender
    worker.metro_station_id = data.metro_station_id
    worker.min_hourly_rate = data.min_hourly_rate
    if resume_completed is not None:
        worker.resume_completed = resume_completed

    await session.flush()
    worker = await get_worker_by_user_id(session, user.id)
    assert worker is not None
    return _worker_to_profile(worker)


async def save_worker_registration(
    session: AsyncSession,
    user: User,
    *,
    first_name: str,
    last_name: str,
    age: int,
    gender: str | None,
    metro_station_id: int,
    min_hourly_rate: Decimal,
    experiences: list[dict],
) -> WorkerProfileRead:
    from app.db.models import Gender

    gender_enum = Gender(gender) if gender else None
    profile = await upsert_worker_profile(
        session,
        user,
        WorkerProfileUpdate(
            first_name=first_name,
            last_name=last_name,
            age=age,
            gender=gender_enum,
            metro_station_id=metro_station_id,
            min_hourly_rate=min_hourly_rate,
        ),
        resume_completed=True,
    )
    worker = await get_worker_by_user_id(session, user.id)
    assert worker is not None

    for exp in list(worker.experiences):
        await session.delete(exp)
    await session.flush()

    for exp_data in experiences:
        session.add(
            WorkerExperience(
                worker_id=worker.id,
                category_id=exp_data["category_id"],
                role_title=exp_data["role_title"],
                duration_months=exp_data["duration_months"],
                description=exp_data.get("description"),
            )
        )

    await session.flush()
    worker = await get_worker_by_user_id(session, user.id)
    assert worker is not None
    return _worker_to_profile(worker)


async def list_worker_experiences(session: AsyncSession, user: User) -> list:
    worker = await get_worker_by_user_id(session, user.id)
    if worker is None:
        return []
    profile = _worker_to_profile(worker)
    return profile.experiences


async def add_worker_experience(
    session: AsyncSession, user: User, data: WorkerExperienceCreate
) -> WorkerProfileRead:
    worker = await get_worker_by_user_id(session, user.id)
    if worker is None:
        raise ValueError("Worker profile not found")

    category_exists = await session.scalar(select(JobCategory.id).where(JobCategory.id == data.category_id))
    if not category_exists:
        raise ValueError("Category not found")

    session.add(
        WorkerExperience(
            worker_id=worker.id,
            category_id=data.category_id,
            role_title=data.role_title,
            duration_months=data.duration_months,
            description=data.description,
        )
    )
    await session.flush()
    worker = await get_worker_by_user_id(session, user.id)
    assert worker is not None
    return _worker_to_profile(worker)


async def delete_worker_experience(session: AsyncSession, user: User, experience_id: UUID) -> WorkerProfileRead:
    worker = await get_worker_by_user_id(session, user.id)
    if worker is None:
        raise ValueError("Worker profile not found")

    exp = await session.scalar(
        select(WorkerExperience).where(
            WorkerExperience.id == experience_id,
            WorkerExperience.worker_id == worker.id,
        )
    )
    if exp is None:
        raise ValueError("Experience not found")

    await session.delete(exp)
    await session.flush()
    worker = await get_worker_by_user_id(session, user.id)
    assert worker is not None
    return _worker_to_profile(worker)


async def get_metro_station_by_id(session: AsyncSession, station_id: int) -> MetroStation | None:
    return await session.scalar(
        select(MetroStation).where(MetroStation.id == station_id, MetroStation.is_active.is_(True))
    )


async def search_metro_stations(session: AsyncSession, query: str, limit: int = 10) -> list[MetroStation]:
    stmt = select(MetroStation).where(MetroStation.is_active.is_(True))
    if query.strip():
        stmt = stmt.where(MetroStation.name.ilike(f"%{query.strip()}%"))
    stmt = stmt.order_by(MetroStation.name).limit(limit)
    result = await session.scalars(stmt)
    return list(result.all())


async def list_metro_stations_by_line_name(session: AsyncSession, line_name: str) -> list[MetroStation]:
    result = await session.scalars(
        select(MetroStation)
        .where(MetroStation.is_active.is_(True), MetroStation.line_name == line_name)
        .order_by(MetroStation.id)
    )
    return sort_stations_on_line(list(result.all()))


async def list_job_categories(session: AsyncSession) -> list[JobCategory]:
    result = await session.scalars(select(JobCategory).where(JobCategory.is_active.is_(True)))
    return sort_job_categories(list(result.all()))
