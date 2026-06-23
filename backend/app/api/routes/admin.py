from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps_admin import get_current_admin
from app.db.models import Application, Employer, JobRequest, User
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminAnalytics,
    AdminAuditEntryRead,
    AdminStats,
    ModerationQueueEntryRead,
    ModerationUserDetailRead,
    ModerationViolationRead,
    PendingEmployerRead,
)
from app.services import admin_stats_service, audit_log_service, employer_service
from app.services import moderation_violation_service, user_block_service

router = APIRouter(prefix="/admin", tags=["admin"])


async def _employer_with_user(
    session: AsyncSession, employer_id: UUID
) -> tuple[Employer, User] | None:
    row = await session.execute(
        select(Employer, User)
        .join(User, Employer.user_id == User.id)
        .where(Employer.id == employer_id)
    )
    item = row.one_or_none()
    if item is None:
        return None
    return item[0], item[1]


def _platform_stats_to_admin(stats: admin_stats_service.PlatformStats) -> AdminStats:
    return AdminStats(
        workers_count=stats.workers_total,
        employers_count=stats.employers_total,
        jobs_count=stats.jobs_total,
        pending_verifications=stats.employers_unverified,
        users_blocked=stats.users_blocked,
        moderation_flagged_users=stats.moderation_flagged_users,
        violations_total=stats.violations_total,
    )


def _queue_entry(summary: moderation_violation_service.FlaggedUserSummary) -> ModerationQueueEntryRead:
    user = summary.user
    flagged_at = user.moderation_flagged_at
    if flagged_at is None:
        raise ValueError("Queue entry requires moderation_flagged_at")
    return ModerationQueueEntryRead(
        telegram_id=user.telegram_id,
        username=user.username,
        violation_count=summary.violation_count,
        is_blocked=bool(user.is_blocked),
        flagged_at=flagged_at,
    )


def _violation_read(item) -> ModerationViolationRead:
    return ModerationViolationRead(
        id=item.id,
        field=item.field,
        category=item.category,
        matched_term=item.matched_term,
        raw_snippet=item.raw_snippet,
        source=item.source.value if hasattr(item.source, "value") else str(item.source),
        created_at=item.created_at,
    )


@router.get("/stats", response_model=AdminStats)
async def admin_stats(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminStats:
    stats = await admin_stats_service.get_platform_stats(session)
    return _platform_stats_to_admin(stats)


@router.get("/analytics", response_model=AdminAnalytics)
async def admin_analytics(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminAnalytics:
    stats = await admin_stats_service.get_platform_stats(session)
    base = _platform_stats_to_admin(stats)

    applications_by_status: dict[str, int] = {}
    app_rows = await session.execute(
        select(Application.status, func.count()).group_by(Application.status)
    )
    for status, count in app_rows.all():
        key = status.value if hasattr(status, "value") else str(status)
        applications_by_status[key] = count

    jobs_by_status: dict[str, int] = {}
    job_rows = await session.execute(
        select(JobRequest.status, func.count()).group_by(JobRequest.status)
    )
    for status, count in job_rows.all():
        key = status.value if hasattr(status, "value") else str(status)
        jobs_by_status[key] = count

    return AdminAnalytics(
        **base.model_dump(),
        applications_by_status=applications_by_status,
        jobs_by_status=jobs_by_status,
    )


@router.get("/employers/pending", response_model=list[PendingEmployerRead])
async def list_pending_employers(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[PendingEmployerRead]:
    rows = await admin_stats_service.list_unverified_employers(session, limit=50)
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


@router.post("/employers/{employer_id}/verify")
async def verify_employer(
    employer_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    employer = await _employer_with_user(session, employer_id)
    if employer is None:
        raise HTTPException(status_code=404, detail="Employer not found")
    emp, user = employer
    result = await employer_service.verify_employer_by_telegram_id(
        session,
        user.telegram_id,
        actor_telegram_id=admin.telegram_id,
    )
    if result.employer is None:
        raise HTTPException(status_code=404, detail=result.message)
    await session.commit()
    return {"status": "verified", "employer_id": str(emp.id)}


@router.post("/employers/{employer_id}/reject")
async def reject_employer(
    employer_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    row = await _employer_with_user(session, employer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Employer not found")
    employer, user = row

    await audit_log_service.record_audit(
        session,
        action="employer.reject",
        actor_telegram_id=admin.telegram_id,
        target_user=user,
        details={
            "company_name": employer.company_name,
            "employer_id": str(employer_id),
            "entity_type": "employer_profile",
            "entity_id": str(employer_id),
        },
    )
    await session.commit()
    return {"status": "rejected", "employer_id": str(employer_id)}


@router.get("/audit", response_model=list[AdminAuditEntryRead])
async def list_audit_logs(
    limit: int = 20,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminAuditEntryRead]:
    entries = await audit_log_service.list_recent_audit(session, limit=min(limit, 100))
    out: list[AdminAuditEntryRead] = []
    for entry in entries:
        details = entry.details or {}
        entity_type = str(details.get("entity_type") or "user")
        entity_id = str(
            details.get("entity_id")
            or details.get("employer_id")
            or entry.target_user_id
            or entry.target_telegram_id
            or entry.id
        )
        out.append(
            AdminAuditEntryRead(
                id=str(entry.id),
                actor_id=str(entry.actor_telegram_id) if entry.actor_telegram_id else None,
                action=entry.action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=details,
                created_at=entry.created_at.isoformat(),
            )
        )
    return out


@router.get("/moderation/queue", response_model=list[ModerationQueueEntryRead])
async def list_moderation_queue(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[ModerationQueueEntryRead]:
    queue = await moderation_violation_service.list_moderation_queue(session)
    return [_queue_entry(item) for item in queue]


@router.get("/moderation/users/{telegram_id}", response_model=ModerationUserDetailRead)
async def get_moderation_user_detail(
    telegram_id: int,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ModerationUserDetailRead:
    user, violations = await moderation_violation_service.get_violations_by_telegram_id(
        session,
        telegram_id,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    violation_count = await moderation_violation_service.count_user_violations(session, user.id)
    return ModerationUserDetailRead(
        telegram_id=user.telegram_id,
        username=user.username,
        is_blocked=bool(user.is_blocked),
        flagged_at=user.moderation_flagged_at,
        violation_count=violation_count,
        violations=[_violation_read(item) for item in violations],
    )


@router.post("/moderation/users/{telegram_id}/block")
async def block_moderation_user(
    telegram_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | bool]:
    result = await user_block_service.block_user(
        session,
        telegram_id,
        actor_telegram_id=admin.telegram_id,
    )
    if result.user is None:
        raise HTTPException(status_code=404, detail=result.message)
    await session.commit()
    return {"status": "blocked", "changed": result.changed, "message": result.message}


@router.post("/moderation/users/{telegram_id}/unblock")
async def unblock_moderation_user(
    telegram_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | bool]:
    result = await user_block_service.unblock_user(
        session,
        telegram_id,
        actor_telegram_id=admin.telegram_id,
    )
    if result.user is None:
        raise HTTPException(status_code=404, detail=result.message)
    await session.commit()
    return {"status": "unblocked", "changed": result.changed, "message": result.message}


@router.post("/moderation/users/{telegram_id}/dismiss")
async def dismiss_moderation_user(
    telegram_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | bool]:
    result = await moderation_violation_service.dismiss_moderation_review(
        session,
        telegram_id,
        actor_telegram_id=admin.telegram_id,
    )
    if result.user is None:
        raise HTTPException(status_code=404, detail=result.message)
    await session.commit()
    return {"status": "dismissed", "changed": result.changed, "message": result.message}
