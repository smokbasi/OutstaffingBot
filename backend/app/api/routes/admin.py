from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps_admin import get_current_admin
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminAnalytics,
    AdminEmployerRead,
    AdminJobRead,
    AdminStats,
    AdminWorkerRead,
    PendingEmployerRead,
    PendingWorkerRead,
)
from app.services import admin_service, audit_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def admin_stats(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminStats:
    return await admin_service.get_admin_stats(session)


@router.get("/analytics", response_model=AdminAnalytics)
async def admin_analytics(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminAnalytics:
    return await admin_service.get_analytics(session)


@router.get("/workers", response_model=list[AdminWorkerRead])
async def list_workers(
    limit: int = 50,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminWorkerRead]:
    return await admin_service.list_workers(session, limit=min(limit, 100))


@router.get("/employers", response_model=list[AdminEmployerRead])
async def list_employers(
    limit: int = 50,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminEmployerRead]:
    return await admin_service.list_employers(session, limit=min(limit, 100))


@router.get("/jobs", response_model=list[AdminJobRead])
async def list_jobs(
    limit: int = 50,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminJobRead]:
    return await admin_service.list_jobs(session, limit=min(limit, 100))


@router.get("/employers/pending", response_model=list[PendingEmployerRead])
async def list_pending_employers(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[PendingEmployerRead]:
    return await admin_service.list_pending_employers(session)


@router.post("/employers/{employer_id}/verify")
async def verify_employer(
    employer_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    employer = await admin_service.verify_employer(
        session, employer_id, actor_id=admin.id, approve=True
    )
    if employer is None:
        raise HTTPException(status_code=404, detail="Employer not found")
    await session.commit()
    return {"status": "verified", "employer_id": str(employer.id)}


@router.post("/employers/{employer_id}/reject")
async def reject_employer(
    employer_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    employer = await admin_service.verify_employer(
        session, employer_id, actor_id=admin.id, approve=False
    )
    if employer is None:
        raise HTTPException(status_code=404, detail="Employer not found")
    await session.commit()
    return {"status": "rejected", "employer_id": str(employer.id)}


@router.get("/workers/pending", response_model=list[PendingWorkerRead])
async def list_pending_workers(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[PendingWorkerRead]:
    return await admin_service.list_pending_workers(session)


@router.post("/workers/{worker_id}/verify")
async def verify_worker(
    worker_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    worker = await admin_service.verify_worker(
        session, worker_id, actor_id=admin.id, approve=True
    )
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    await session.commit()
    return {"status": "verified", "worker_id": str(worker.id)}


@router.post("/workers/{worker_id}/reject")
async def reject_worker(
    worker_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    worker = await admin_service.verify_worker(
        session, worker_id, actor_id=admin.id, approve=False
    )
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    await session.commit()
    return {"status": "rejected", "worker_id": str(worker.id)}


@router.get("/audit")
async def list_audit_logs(
    limit: int = 20,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    entries = await audit_service.list_recent_audit_logs(session, limit=min(limit, 100))
    return [
        {
            "id": str(entry.id),
            "actor_id": str(entry.actor_id) if entry.actor_id else None,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "metadata": entry.metadata_,
            "created_at": entry.created_at.isoformat(),
        }
        for entry in entries
    ]
