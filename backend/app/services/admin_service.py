from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Application,
    ApplicationStatus,
    Employer,
    JobRequest,
    User,
    VerificationStatus,
    Worker,
)
from app.schemas.admin import AdminAnalytics, AdminStats, PendingEmployerRead
from app.services import audit_service


async def get_admin_stats(session: AsyncSession) -> AdminStats:
    workers = await session.scalar(select(func.count()).select_from(Worker)) or 0
    employers = await session.scalar(select(func.count()).select_from(Employer)) or 0
    jobs = await session.scalar(select(func.count()).select_from(JobRequest)) or 0
    pending_verifications = await session.scalar(
        select(func.count())
        .select_from(Employer)
        .where(Employer.verification_status == VerificationStatus.pending)
    ) or 0
    return AdminStats(
        workers_count=workers,
        employers_count=employers,
        jobs_count=jobs,
        pending_verifications=pending_verifications,
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
