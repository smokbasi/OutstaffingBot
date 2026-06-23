from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.complaint import (
    ComplaintRead,
    WorkerComplaintContextResponse,
    WorkerComplaintCreate,
)
from app.services import complaint_service, user_block_service, worker_service

router = APIRouter(prefix="/complaints", tags=["complaints"])


async def _get_worker_or_404(session: AsyncSession, user: User):
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return worker


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


@router.get("/my-context", response_model=WorkerComplaintContextResponse)
async def get_worker_complaint_context(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkerComplaintContextResponse:
    worker = await _get_worker_or_404(session, user)
    return await complaint_service.get_worker_complaint_context(session, worker)


@router.post("", response_model=ComplaintRead, status_code=201)
async def create_worker_complaint(
    data: WorkerComplaintCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ComplaintRead:
    worker = await _get_worker_or_404(session, user)
    try:
        complaint = await complaint_service.create_worker_complaint(
            session,
            worker,
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
