from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobCategory, MetroStation, User, Worker, WorkerPreferences
from app.schemas.preferences import WorkerPreferencesRead, WorkerPreferencesUpdate
from app.services.worker_service import get_worker_by_user_id


async def get_preferences(session: AsyncSession, user: User) -> WorkerPreferencesRead:
    worker = await get_worker_by_user_id(session, user.id)
    preferences = await session.scalar(
        select(WorkerPreferences).where(WorkerPreferences.user_id == user.id)
    )
    return WorkerPreferencesRead(
        category_ids=list(preferences.category_ids or []) if preferences else [],
        metro_station_ids=list(preferences.metro_station_ids or []) if preferences else [],
        min_hourly_rate=preferences.min_hourly_rate if preferences else None,
        notifications_enabled=worker.notifications_enabled if worker else True,
    )


async def _validate_category_ids(session: AsyncSession, category_ids: list[int]) -> None:
    if not category_ids:
        return
    found = await session.scalars(
        select(JobCategory.id).where(
            JobCategory.id.in_(category_ids),
            JobCategory.is_active.is_(True),
        )
    )
    if len(list(found.all())) != len(set(category_ids)):
        raise ValueError("Unknown category in preferences")


async def _validate_metro_ids(session: AsyncSession, metro_station_ids: list[int]) -> None:
    if not metro_station_ids:
        return
    found = await session.scalars(
        select(MetroStation.id).where(
            MetroStation.id.in_(metro_station_ids),
            MetroStation.is_active.is_(True),
        )
    )
    if len(list(found.all())) != len(set(metro_station_ids)):
        raise ValueError("Unknown metro station in preferences")


async def upsert_preferences(
    session: AsyncSession,
    user: User,
    data: WorkerPreferencesUpdate,
) -> WorkerPreferencesRead:
    worker = await get_worker_by_user_id(session, user.id)
    if worker is None:
        raise ValueError("Worker profile not found")

    preferences = await session.scalar(
        select(WorkerPreferences).where(WorkerPreferences.user_id == user.id)
    )
    if preferences is None:
        preferences = WorkerPreferences(user_id=user.id)
        session.add(preferences)

    if data.category_ids is not None:
        await _validate_category_ids(session, data.category_ids)
        preferences.category_ids = data.category_ids or None

    if data.metro_station_ids is not None:
        await _validate_metro_ids(session, data.metro_station_ids)
        preferences.metro_station_ids = data.metro_station_ids or None

    if data.min_hourly_rate is not None:
        preferences.min_hourly_rate = data.min_hourly_rate

    if data.notifications_enabled is not None:
        worker.notifications_enabled = data.notifications_enabled
        preferences.push_enabled = data.notifications_enabled

    await session.flush()
    return await get_preferences(session, user)


async def set_notifications_enabled(
    session: AsyncSession,
    user: User,
    *,
    enabled: bool,
) -> WorkerPreferencesRead:
    return await upsert_preferences(
        session,
        user,
        WorkerPreferencesUpdate(notifications_enabled=enabled),
    )
