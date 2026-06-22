from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Application,
    ApplicationStatus,
    Employer,
    JobRequest,
    User,
    VerificationStatus,
    Worker,
    WorkerExperience,
)
from app.schemas.admin import AdminAnalytics, AdminStats, PendingEmployerRead, PendingWorkerRead
from app.services import audit_service


async def get_admin_stats(session: AsyncSession) -> AdminStats:
    workers = await session.scalar(select(func.count()).select_from(Worker)) or 0
    employers = await session.scalar(select(func.count()).select_from(Employer)) or 0
    jobs = await session.scalar(select(func.count()).select_from(JobRequest)) or 0
    pending_employers = await session.scalar(
        select(func.count())
        .select_from(Employer)
        .where(Employer.verification_status == VerificationStatus.pending)
    ) or 0
    pending_workers = await session.scalar(
        select(func.count())
        .select_from(Worker)
        .where(
            Worker.verification_status == VerificationStatus.pending,
            Worker.resume_completed.is_(True),
        )
    ) or 0
    return AdminStats(
        workers_count=workers,
        employers_count=employers,
        jobs_count=jobs,
        pending_verifications=pending_employers + pending_workers,
    )


async def get_analytics(session: AsyncSession) -> AdminAnalytics:
    stats = await get_admin_stats(session)
    applications_by_status: dict[str, int] = {}
    rows = await session.execute(
        select(Application.status, func.count())
        .group_by(Application.status)
    )
    for status, count in rows.all():
        applications_by_status[status.value if hasattr(status, "value") else str(status)] = count

    jobs_by_status: dict[str, int] = {}
    job_rows = await session.execute(
        select(JobRequest.status, func.count()).group_by(JobRequest.status)
    )
    for status, count in job_rows.all():
        jobs_by_status[status.value if hasattr(status, "value") else str(status)] = count

    return AdminAnalytics(
        workers_count=stats.workers_count,
        employers_count=stats.employers_count,
        jobs_count=stats.jobs_count,
        pending_verifications=stats.pending_verifications,
        applications_by_status=applications_by_status,
        jobs_by_status=jobs_by_status,
    )


async def list_pending_employers(session: AsyncSession) -> list[PendingEmployerRead]:
    stmt = (
        select(Employer, User)
        .join(User, Employer.user_id == User.id)
        .where(Employer.verification_status == VerificationStatus.pending)
        .order_by(Employer.created_at.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        PendingEmployerRead(
            id=employer.id,
            company_name=employer.company_name,
            contact_phone=employer.contact_phone,
            contact_person=employer.contact_person,
            telegram_id=user.telegram_id,
            username=user.username,
            created_at=employer.created_at,
        )
        for employer, user in rows
    ]


async def verify_employer(
    session: AsyncSession,
    employer_id: UUID,
    *,
    actor_id: UUID | None,
    approve: bool,
) -> Employer | None:
    employer = await session.scalar(select(Employer).where(Employer.id == employer_id))
    if employer is None:
        return None

    new_status = VerificationStatus.verified if approve else VerificationStatus.rejected
    employer.verification_status = new_status
    await session.flush()

    await audit_service.log_audit(
        session,
        actor_id=actor_id,
        action="employer.verify" if approve else "employer.reject",
        entity_type="employer",
        entity_id=employer.id,
        metadata={"verification_status": new_status.value},
    )
    return employer


async def list_pending_workers(session: AsyncSession) -> list[PendingWorkerRead]:
    stmt = (
        select(Worker, User)
        .join(User, Worker.user_id == User.id)
        .options(
            selectinload(Worker.experiences).selectinload(WorkerExperience.category),
            selectinload(Worker.metro_station),
        )
        .where(
            Worker.verification_status == VerificationStatus.pending,
            Worker.resume_completed.is_(True),
        )
        .order_by(Worker.created_at.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        PendingWorkerRead(
            id=worker.id,
            first_name=worker.first_name,
            last_name=worker.last_name,
            age=worker.age,
            metro_station_name=worker.metro_station.name if worker.metro_station else None,
            categories=[
                exp.category.name_ru
                for exp in worker.experiences
                if exp.category is not None
            ],
            telegram_id=user.telegram_id,
            username=user.username,
            created_at=worker.created_at,
        )
        for worker, user in rows
    ]


async def verify_worker(
    session: AsyncSession,
    worker_id: UUID,
    *,
    actor_id: UUID | None,
    approve: bool,
) -> Worker | None:
    worker = await session.scalar(select(Worker).where(Worker.id == worker_id))
    if worker is None:
        return None

    new_status = VerificationStatus.verified if approve else VerificationStatus.rejected
    worker.verification_status = new_status
    await session.flush()

    await audit_service.log_audit(
        session,
        actor_id=actor_id,
        action="worker.verify" if approve else "worker.reject",
        entity_type="worker",
        entity_id=worker.id,
        metadata={"verification_status": new_status.value},
    )
    return worker
