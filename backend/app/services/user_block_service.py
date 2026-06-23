"""User block/unblock and enforcement (Phase 9.7)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Employer, User, Worker
from app.services import audit_log_service, moderation_violation_service, user_service

ACCOUNT_BLOCKED_MESSAGE = "Ваш аккаунт заблокирован."


class UserBlockedError(Exception):
    def __init__(self, message: str = ACCOUNT_BLOCKED_MESSAGE) -> None:
        self.message = message
        super().__init__(message)


def ensure_not_blocked(user: User) -> None:
    if user.is_blocked:
        raise UserBlockedError()


@dataclass(frozen=True)
class BlockActionResult:
    user: User | None
    changed: bool
    message: str


async def block_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    actor_telegram_id: int,
) -> BlockActionResult:
    user = await user_service.get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return BlockActionResult(user=None, changed=False, message="Пользователь не найден.")

    if user.is_blocked:
        return BlockActionResult(user=user, changed=False, message="Пользователь уже заблокирован.")

    user.is_blocked = True
    moderation_violation_service.clear_moderation_review_flag(user)
    await session.flush()
    await audit_log_service.record_audit(
        session,
        action="moderation.user_block",
        actor_telegram_id=actor_telegram_id,
        target_user=user,
        details={"previous_is_blocked": False},
    )
    return BlockActionResult(user=user, changed=True, message="Пользователь заблокирован.")


async def unblock_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    actor_telegram_id: int,
) -> BlockActionResult:
    user = await user_service.get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return BlockActionResult(user=None, changed=False, message="Пользователь не найден.")

    if not user.is_blocked:
        return BlockActionResult(user=user, changed=False, message="Пользователь не был заблокирован.")

    user.is_blocked = False
    await session.flush()
    await audit_log_service.record_audit(
        session,
        action="moderation.user_unblock",
        actor_telegram_id=actor_telegram_id,
        target_user=user,
        details={"previous_is_blocked": True},
    )
    return BlockActionResult(user=user, changed=True, message="Пользователь разблокирован.")


async def ensure_worker_not_blocked(session: AsyncSession, worker: Worker) -> None:
    user = getattr(worker, "user", None)
    if user is None and getattr(worker, "user_id", None) is not None:
        user = await session.get(User, worker.user_id)
    if user is None:
        return
    ensure_not_blocked(user)


async def ensure_employer_not_blocked(session: AsyncSession, employer_id) -> None:
    is_blocked = await session.scalar(
        select(User.is_blocked)
        .join(Employer, Employer.user_id == User.id)
        .where(Employer.id == employer_id)
    )
    if is_blocked is True:
        raise UserBlockedError()
