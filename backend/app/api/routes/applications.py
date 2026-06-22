from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationRead,
    ConflictingShiftInfo,
    ShiftConflictResponse,
)
from app.services import application_service, worker_service

router = APIRouter(prefix="/applications", tags=["applications"])


async def _get_worker_or_404(session: AsyncSession, user: User):
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return worker


def _conflict_response(exc: application_service.ShiftConflictError) -> JSONResponse:
    app = exc.conflicting_application
    slot = app.shift_slot
    job = app.job_request
    body = ShiftConflictResponse(
        detail=(
            f"У вас уже есть смена {slot.shift_date.strftime('%d.%m.%Y')} "
            f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}. "
            "Отмените её, чтобы откликнуться на новую."
        ),
        conflicting=ConflictingShiftInfo(
            application_id=app.id,
            shift_date=slot.shift_date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            job_title=job.title if job else "",
        ),
    )
    return JSONResponse(status_code=409, content=body.model_dump(mode="json"))


@router.post("", response_model=ApplicationRead, status_code=201)
async def apply_to_shift(
    data: ApplicationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    worker = await _get_worker_or_404(session, user)
    try:
        result = await application_service.apply_to_shift(
            session,
            worker,
            data.shift_slot_id,
            cancel_conflicting_id=data.cancel_conflicting_id,
        )
    except application_service.ShiftConflictError as exc:
        return _conflict_response(exc)
    except application_service.AlreadyAppliedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except application_service.CancelConflictMismatchError as exc:
        raise HTTPException(
            status_code=400,
            detail="Указанная заявка не совпадает с конфликтующей сменой",
        ) from exc
    except application_service.SlotUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except application_service.WorkerNotVerifiedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    await session.commit()
    return result


@router.delete("/{application_id}", response_model=ApplicationRead)
async def cancel_application(
    application_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationRead:
    worker = await _get_worker_or_404(session, user)
    try:
        result = await application_service.cancel_application(session, worker, application_id)
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except application_service.ApplicationNotCancellableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    return result


@router.get("/mine", response_model=ApplicationListResponse)
async def list_my_applications(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationListResponse:
    worker = await _get_worker_or_404(session, user)
    return await application_service.list_my_applications(session, worker)
