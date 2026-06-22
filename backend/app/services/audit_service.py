import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, User


async def log_audit(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | UUID,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        metadata_=metadata,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_recent_audit_logs(
    session: AsyncSession,
    *,
    limit: int = 20,
) -> list[AuditLog]:
    result = await session.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return list(result.all())


def format_audit_entry(entry: AuditLog) -> str:
    actor = str(entry.actor_id)[:8] if entry.actor_id else "system"
    ts = entry.created_at.strftime("%d.%m %H:%M") if isinstance(entry.created_at, datetime) else "—"
    return f"{ts} | {entry.action} | {entry.entity_type}:{entry.entity_id[:8]}… | {actor}"
