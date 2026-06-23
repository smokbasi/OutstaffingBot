"""Persist moderation violations and flag users at threshold (Phase 9.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models import ModerationViolationLog, ModerationViolationSource, User
from app.services import audit_log_service, user_service
from app.services.content_moderation_service import ContentRejectedError


@dataclass(frozen=True)
class FlaggedUserSummary:
    user: User
    violation_count: int


@dataclass(frozen=True)
class ModerationReviewResult:
    user: User | None
    changed: bool
    message: str


async def count_user_violations(session: AsyncSession, user_id: UUID) -> int:
    total = await session.scalar(
        select(func.count())
        .select_from(ModerationViolationLog)
        .where(ModerationViolationLog.user_id == user_id)
    )
    return int(total or 0)


async def record_content_rejection(
    session: AsyncSession,
    user: User,
    exc: ContentRejectedError,
    *,
    source: ModerationViolationSource,
) -> bool:
    """Log violation and flag user when threshold is reached. Returns True if newly flagged."""
    violation = exc.violation
    session.add(
        ModerationViolationLog(
            user_id=user.id,
            telegram_id=user.telegram_id,
            field=violation.field,
            category=violation.category,
            matched_term=violation.matched_term,
            raw_snippet=violation.raw_snippet,
            normalized_snippet=violation.normalized_snippet,
            source=source,
        )
    )
    await session.flush()

    threshold = get_settings().moderation_violation_threshold
    if threshold <= 0:
        return False

    total = await count_user_violations(session, user.id)
    if total >= threshold and user.moderation_flagged_at is None:
        user.moderation_flagged_at = datetime.now(UTC)
        await session.flush()
        return True
    return False


async def list_moderation_queue(session: AsyncSession) -> list[FlaggedUserSummary]:
    """Users flagged for admin review (moderation_flagged_at set)."""
    stmt = (
        select(User)
        .options(selectinload(User.moderation_violations))
        .where(User.moderation_flagged_at.is_not(None))
        .order_by(User.moderation_flagged_at.desc())
    )
    users = list(await session.scalars(stmt))
    summaries: list[FlaggedUserSummary] = []
    for user in users:
        total = await count_user_violations(session, user.id)
        summaries.append(FlaggedUserSummary(user=user, violation_count=total))
    return summaries


async def get_violations_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> tuple[User | None, list[ModerationViolationLog]]:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        return None, []

    stmt = (
        select(ModerationViolationLog)
        .where(ModerationViolationLog.user_id == user.id)
        .order_by(ModerationViolationLog.created_at.desc())
    )
    violations = list(await session.scalars(stmt))
    return user, violations


def clear_moderation_review_flag(user: User) -> bool:
    """Remove user from admin review queue. Returns True if flag was cleared."""
    if user.moderation_flagged_at is None:
        return False
    user.moderation_flagged_at = None
    return True


async def dismiss_moderation_review(
    session: AsyncSession,
    telegram_id: int,
    *,
    actor_telegram_id: int,
) -> ModerationReviewResult:
    """Admin rejects ban request — user stays active, removed from review queue."""
    user = await user_service.get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return ModerationReviewResult(
            user=None,
            changed=False,
            message="Пользователь не найден.",
        )

    if user.moderation_flagged_at is None:
        return ModerationReviewResult(
            user=user,
            changed=False,
            message="Пользователь не в очереди модерации.",
        )

    clear_moderation_review_flag(user)
    await session.flush()
    await audit_log_service.record_audit(
        session,
        action="moderation.review_dismiss",
        actor_telegram_id=actor_telegram_id,
        target_user=user,
        details={"violation_count": await count_user_violations(session, user.id)},
    )
    return ModerationReviewResult(
        user=user,
        changed=True,
        message="Заявка на блокировку отклонена, пользователь снят с review.",
    )
