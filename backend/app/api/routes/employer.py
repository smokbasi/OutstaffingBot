from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employer, get_current_user
from app.db.models import ApplicationStatus, Employer, User
from app.db.session import get_db_session
from app.schemas.employer import EmployerProfileRead, EmployerProfileUpdate
from app.schemas.application import ApplicationListResponse, ApplicationRead, ApplicationStatusUpdate
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


@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications(
    job_id: UUID | None = Query(default=None),
    status: ApplicationStatus | None = Query(default=None),
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationListResponse:
    return await application_service.list_employer_applications(
        session,
        employer.id,
        job_id=job_id,
        status=status,
    )


@router.get("/jobs/{job_id}/applications", response_model=ApplicationListResponse)
async def list_job_applications(
    job_id: UUID,
    status: ApplicationStatus | None = Query(default=None),
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationListResponse:
    job = await job_service.get_job_request(session, employer.id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job request not found")
    return await application_service.list_employer_applications(
        session,
        employer.id,
        job_id=job_id,
        status=status,
    )


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
async def update_application_status(
    application_id: UUID,
    data: ApplicationStatusUpdate,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    if data.status == ApplicationStatus.accepted:
        try:
            result = await application_service.accept_application(session, employer.id, application_id)
        except application_service.ApplicationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except application_service.ApplicationNotAcceptableError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except application_service.SlotUnavailableError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif data.status == ApplicationStatus.rejected:
        try:
            result = await application_service.reject_application(session, employer.id, application_id)
        except application_service.ApplicationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except application_service.ApplicationNotRejectableError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=400, detail="Only accept or reject is supported")

    await session.commit()
    return result
