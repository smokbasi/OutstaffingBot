from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.worker import WorkerExperienceCreate, WorkerExperienceRead, WorkerProfileRead, WorkerProfileUpdate
from app.services import worker_service

router = APIRouter(prefix="/worker", tags=["worker"])


@router.get("/profile", response_model=WorkerProfileRead)
async def get_worker_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkerProfileRead:
    profile = await worker_service.get_worker_profile(session, user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return profile


@router.put("/profile", response_model=WorkerProfileRead)
async def update_worker_profile(
    data: WorkerProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkerProfileRead:
    profile = await worker_service.upsert_worker_profile(session, user, data, resume_completed=True)
    await session.commit()
    return profile


@router.get("/experiences", response_model=list[WorkerExperienceRead])
async def list_experiences(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[WorkerExperienceRead]:
    return await worker_service.list_worker_experiences(session, user)


@router.post("/experiences", response_model=WorkerProfileRead, status_code=201)
async def create_experience(
    data: WorkerExperienceCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkerProfileRead:
    try:
        profile = await worker_service.add_worker_experience(session, user, data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return profile


@router.delete("/experiences/{experience_id}", response_model=WorkerProfileRead)
async def delete_experience(
    experience_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkerProfileRead:
    from uuid import UUID

    try:
        profile = await worker_service.delete_worker_experience(session, user, UUID(experience_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return profile
