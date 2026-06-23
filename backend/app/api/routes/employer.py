from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employer, get_current_user
from app.api.moderation_errors import content_rejected_response
from app.db.models import ApplicationStatus, Employer, ModerationViolationSource, User
from app.db.session import get_db_session
from app.schemas.employer import EmployerProfileRead, EmployerProfileUpdate
from app.schemas.application import ApplicationListResponse, ApplicationRead, ApplicationStatusUpdate
from app.schemas.complaint import (
    ComplaintRead,
    EmployerComplaintApplicationsResponse,
    EmployerComplaintCreate,
    EmployerComplaintJobsResponse,
)
from app.schemas.job_request import JobRequestCreate, JobRequestRead, JobRequestUpdate
from app.services import application_service, complaint_service, content_moderation_service, employer_service, job_service
from app.services import moderation_violation_service, user_block_service

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
) -> EmployerProfileRead | JSONResponse:
    try:
        profile = await employer_service.upsert_employer_profile(session, user, data)
    except content_moderation_service.ContentRejectedError as exc:
        await moderation_violation_service.record_content_rejection(
            session,
            user,
            exc,
            source=ModerationViolationSource.mini_app,
        )
        await session.commit()
        return content_rejected_response(exc)
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
    except user_block_service.UserBlockedError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except employer_service.EmployerNotVerifiedError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
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
    user: User = Depends(get_current_user),
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> JobRequestRead | JSONResponse:
    if data.status is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        job = await job_service.update_job_request(session, employer.id, job_id, data)
    except user_block_service.UserBlockedError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except content_moderation_service.ContentRejectedError as exc:
        await moderation_violation_service.record_content_rejection(
            session,
            user,
            exc,
            source=ModerationViolationSource.mini_app,
        )
        await session.commit()
        return content_rejected_response(exc)
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


def _map_complaint_error(exc: complaint_service.ComplaintError) -> HTTPException:
    if isinstance(exc, complaint_service.ComplaintNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, complaint_service.ComplaintForbiddenError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, complaint_service.ComplaintDuplicateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, complaint_service.ComplaintValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, complaint_service.ComplaintNotEligibleError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/complaints/jobs", response_model=EmployerComplaintJobsResponse)
async def list_complaint_jobs(
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> EmployerComplaintJobsResponse:
    return await complaint_service.list_employer_complaint_jobs(session, employer)


@router.get(
    "/complaints/jobs/{job_id}/applications",
    response_model=EmployerComplaintApplicationsResponse,
)
async def list_complaint_job_applications(
    job_id: UUID,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> EmployerComplaintApplicationsResponse:
    try:
        return await complaint_service.list_employer_complaint_applications(
            session,
            employer,
            job_id,
        )
    except complaint_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/complaints", response_model=ComplaintRead, status_code=201)
async def create_employer_complaint(
    data: EmployerComplaintCreate,
    employer: Employer = Depends(get_current_employer),
    session: AsyncSession = Depends(get_db_session),
) -> ComplaintRead:
    try:
        complaint = await complaint_service.create_employer_complaint(
            session,
            employer,
            application_id=data.application_id,
            violation_type=data.violation_type,
            description=data.description,
        )
    except user_block_service.UserBlockedError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except complaint_service.ComplaintError as exc:
        raise _map_complaint_error(exc) from exc

    await session.commit()
    return complaint
