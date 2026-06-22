"""Append-only audit log for admin actions (Phase 9.7)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, User


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    actor_telegram_id: int | None = None,
    target_user: User | None = None,
    target_telegram_id: int | None = None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        actor_telegram_id=actor_telegram_id,
        target_user_id=target_user.id if target_user is not None else None,
        target_telegram_id=target_telegram_id
        if target_telegram_id is not None
        else (target_user.telegram_id if target_user is not None else None),
        details=details,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_audit_for_user(
    session: AsyncSession,
    *,
    target_user_id: UUID | None = None,
    target_telegram_id: int | None = None,
    action: str | None = None,
    limit: int = 50,
) -> list[AuditLog]:
    from sqlalchemy import select

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if target_user_id is not None:
        stmt = stmt.where(AuditLog.target_user_id == target_user_id)
    if target_telegram_id is not None:
        stmt = stmt.where(AuditLog.target_telegram_id == target_telegram_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    return list(await session.scalars(stmt))


async def list_recent_audit(
    session: AsyncSession,
    *,
    limit: int = 30,
    target_telegram_id: int | None = None,
    action: str | None = None,
) -> list[AuditLog]:
    return await list_audit_for_user(
        session,
        target_telegram_id=target_telegram_id,
        action=action,
        limit=limit,
    )
