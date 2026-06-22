"""Platform statistics for admin dashboard (Phase 9.8)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Application,
    Employer,
    JobRequest,
    JobRequestStatus,
    ModerationViolationLog,
    User,
    Worker,
)

@dataclass(frozen=True)
class PlatformStats:
    users_total: int
    workers_total: int
    employers_total: int
    users_blocked: int
    employers_unverified: int
    jobs_total: int
    jobs_active: int
    jobs_draft: int
    applications_total: int
    violations_total: int
    moderation_flagged_users: int


async def get_platform_stats(session: AsyncSession) -> PlatformStats:
    users_total = await session.scalar(select(func.count()).select_from(User)) or 0
    workers_total = await session.scalar(select(func.count()).select_from(Worker)) or 0
    employers_total = await session.scalar(select(func.count()).select_from(Employer)) or 0
    users_blocked = await session.scalar(
        select(func.count()).select_from(User).where(User.is_blocked.is_(True))
    ) or 0
    employers_unverified = await session.scalar(
        select(func.count()).select_from(Employer).where(Employer.verified.is_(False))
    ) or 0
    jobs_total = await session.scalar(select(func.count()).select_from(JobRequest)) or 0
    jobs_active = await session.scalar(
        select(func.count())
        .select_from(JobRequest)
        .where(JobRequest.status == JobRequestStatus.active)
    ) or 0
    jobs_draft = await session.scalar(
        select(func.count())
        .select_from(JobRequest)
        .where(JobRequest.status == JobRequestStatus.draft)
    ) or 0
    applications_total = await session.scalar(select(func.count()).select_from(Application)) or 0
    violations_total = await session.scalar(select(func.count()).select_from(ModerationViolationLog)) or 0
    moderation_flagged_users = await session.scalar(
        select(func.count()).select_from(User).where(User.moderation_flagged_at.is_not(None))
    ) or 0

    return PlatformStats(
        users_total=users_total,
        workers_total=workers_total,
        employers_total=employers_total,
        users_blocked=users_blocked,
        employers_unverified=employers_unverified,
        jobs_total=jobs_total,
        jobs_active=jobs_active,
        jobs_draft=jobs_draft,
        applications_total=applications_total,
        violations_total=violations_total,
        moderation_flagged_users=moderation_flagged_users,
    )


async def list_unverified_employers(session: AsyncSession, limit: int = 30) -> list[tuple[Employer, User]]:
    stmt = (
        select(Employer, User)
        .join(User, Employer.user_id == User.id)
        .where(Employer.verified.is_(False))
        .order_by(Employer.created_at.desc())
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [(employer, user) for employer, user in rows.all()]
