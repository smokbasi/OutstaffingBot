from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employer, get_current_user
from app.db.models import Employer, User
from app.db.session import get_db_session
from app.schemas.application import (
    EmployerApplicationListResponse,
    EmployerApplicationRead,
    EmployerApplicationUpdate,
)
from app.schemas.employer import EmployerProfileRead, EmployerProfileUpdate
from app.schemas.job_request import JobRequestCreate, JobRequestRead, JobRequestUpdate
from app.services import application_service, employer_service, job_service

router = APIRouter(prefix="/employer", tags=["employer"])


@router.get("/profile", response_model=EmployerProfileRead)
async def get_employer_profile_route(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EmployerProfileRead:
    profile = await employer_service.get_employer_profile(session, user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Employer profile not found")
    return profile


@router.put("/profile", response_model=EmployerProfileRead)
async def update_employer_profile_route(
    data: EmployerProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EmployerProfileRead:
    profile = await employer_service.upsert_employer_profile(session, user, data)
    await session.commit()
    return profile


@router.post("/jobs", response_model=JobRequestRead, status_code=201)
async def create_job(
    data: JobRequestCreate,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> JobRequestRead:
    try:
        job = await job_service.create_job_request(session, employer.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return job


@router.get("/jobs", response_model=list[JobRequestRead])
async def list_jobs(
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> list[JobRequestRead]:
    return await job_service.list_job_requests(session, employer.id)


@router.get("/jobs/{job_id}", response_model=JobRequestRead)
async def get_job(
    job_id: UUID,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> JobRequestRead:
    job = await job_service.get_job_request(session, employer.id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job request not found")
    return job


@router.patch("/jobs/{job_id}", response_model=JobRequestRead)
async def update_job(
    job_id: UUID,
    data: JobRequestUpdate,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> JobRequestRead:
    if data.status is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        job = await job_service.update_job_request(session, employer.id, job_id, data)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Job request not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    await session.commit()
    return job


@router.get("/jobs/{job_id}/applications", response_model=EmployerApplicationListResponse)
async def list_job_applications(
    job_id: UUID,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> EmployerApplicationListResponse:
    try:
        return await application_service.list_job_applications(session, employer.id, job_id)
    except application_service.JobNotFoundForEmployerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/applications/{application_id}", response_model=EmployerApplicationRead)
async def update_application_status(
    application_id: UUID,
    data: EmployerApplicationUpdate,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> EmployerApplicationRead:
    try:
        result = await application_service.update_application_by_employer(
            session,
            employer.id,
            application_id,
            data.status,
        )
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except application_service.ApplicationNotPendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except application_service.SlotFullError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    return result
