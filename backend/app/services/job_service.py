from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.arq_pool import enqueue_job
from app.db.models import JobCategory, JobRequest, JobRequestStatus, MetroStation, ShiftSlot
from app.schemas.job_request import JobRequestCreate, JobRequestRead, JobRequestUpdate

_ALLOWED_STATUS_TRANSITIONS: dict[JobRequestStatus, set[JobRequestStatus]] = {
    JobRequestStatus.draft: {JobRequestStatus.active, JobRequestStatus.cancelled},
    JobRequestStatus.active: {JobRequestStatus.cancelled},
}


async def _get_job_stmt(job_id: UUID, employer_id: UUID):
    return (
        select(JobRequest)
        .options(
            selectinload(JobRequest.shift_slots),
            selectinload(JobRequest.category),
            selectinload(JobRequest.metro_station),
        )
        .where(JobRequest.id == job_id, JobRequest.employer_id == employer_id)
    )


def _job_to_read(job: JobRequest) -> JobRequestRead:
    shift_slots = sorted(job.shift_slots, key=lambda slot: (slot.shift_date, slot.start_time))
    return JobRequestRead(
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
        required_gender=job.required_gender,
        min_age=job.min_age,
        max_age=job.max_age,
        dress_code=job.dress_code,
        contact_info=job.contact_info,
        includes_lunch=job.includes_lunch,
        status=job.status,
        post_to_groups=job.post_to_groups,
        notify_matching_workers=job.notify_matching_workers,
        shift_slots=[
            {
                "id": slot.id,
                "shift_date": slot.shift_date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "slots_total": slot.slots_total,
                "slots_filled": slot.slots_filled,
            }
            for slot in shift_slots
        ],
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def _validate_references(session: AsyncSession, data: JobRequestCreate) -> None:
    category_exists = await session.scalar(
        select(JobCategory.id).where(JobCategory.id == data.category_id, JobCategory.is_active.is_(True))
    )
    if not category_exists:
        raise ValueError("Category not found")

    metro_exists = await session.scalar(
        select(MetroStation.id).where(
            MetroStation.id == data.metro_station_id,
            MetroStation.is_active.is_(True),
        )
    )
    if not metro_exists:
        raise ValueError("Metro station not found")


async def create_job_request(
    session: AsyncSession,
    employer_id: UUID,
    data: JobRequestCreate,
) -> JobRequestRead:
    await _validate_references(session, data)

    job = JobRequest(
        employer_id=employer_id,
        category_id=data.category_id,
        title=data.title,
        description=data.description,
        metro_station_id=data.metro_station_id,
        address=data.address,
        hourly_rate=data.hourly_rate,
        workers_needed=data.workers_needed,
        min_experience_months=data.min_experience_months,
        required_gender=data.required_gender,
        min_age=data.min_age,
        max_age=data.max_age,
        dress_code=data.dress_code,
        contact_info=data.contact_info,
        includes_lunch=data.includes_lunch,
        status=JobRequestStatus.draft,
        post_to_groups=data.post_to_groups,
        notify_matching_workers=data.notify_matching_workers,
    )
    session.add(job)
    await session.flush()

    for slot_data in data.shift_slots:
        slots_total = slot_data.slots_total or data.workers_needed
        session.add(
            ShiftSlot(
                job_request_id=job.id,
                shift_date=slot_data.shift_date,
                start_time=slot_data.start_time,
                end_time=slot_data.end_time,
                slots_total=slots_total,
            )
        )

    await session.flush()
    job = await session.scalar(await _get_job_stmt(job.id, employer_id))
    assert job is not None
    return _job_to_read(job)


async def list_job_requests(session: AsyncSession, employer_id: UUID) -> list[JobRequestRead]:
    stmt = (
        select(JobRequest)
        .options(
            selectinload(JobRequest.shift_slots),
            selectinload(JobRequest.category),
            selectinload(JobRequest.metro_station),
        )
        .where(JobRequest.employer_id == employer_id)
        .order_by(JobRequest.created_at.desc())
    )
    jobs = list(await session.scalars(stmt))
    return [_job_to_read(job) for job in jobs]


async def get_job_request(
    session: AsyncSession,
    employer_id: UUID,
    job_id: UUID,
) -> JobRequestRead | None:
    job = await session.scalar(await _get_job_stmt(job_id, employer_id))
    if job is None:
        return None
    return _job_to_read(job)


def _validate_status_transition(current: JobRequestStatus, new_status: JobRequestStatus) -> None:
    if current == new_status:
        return
    allowed = _ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot transition from {current.value} to {new_status.value}")


async def update_job_request(
    session: AsyncSession,
    employer_id: UUID,
    job_id: UUID,
    data: JobRequestUpdate,
) -> JobRequestRead:
    job = await session.scalar(await _get_job_stmt(job_id, employer_id))
    if job is None:
        raise ValueError("Job request not found")

    previous_status = job.status
    if data.status is not None:
        _validate_status_transition(job.status, data.status)
        job.status = data.status

    if data.includes_lunch is not None:
        job.includes_lunch = data.includes_lunch

    await session.flush()
    job = await session.scalar(await _get_job_stmt(job_id, employer_id))
    assert job is not None

    if (
        previous_status != JobRequestStatus.active
        and job.status == JobRequestStatus.active
        and job.notify_matching_workers
    ):
        await enqueue_job("match_workers_for_job", str(job.id))

    return _job_to_read(job)
