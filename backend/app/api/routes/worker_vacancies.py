from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.vacancy import VacancyDetail, VacancyFilters, VacancyListResponse
from app.services import matching_service, worker_service

router = APIRouter(prefix="/worker/vacancies", tags=["worker-vacancies"])


async def _get_worker_or_404(session: AsyncSession, user: User):
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return worker


@router.get("", response_model=VacancyListResponse)
async def list_worker_vacancies(
    category_id: int | None = Query(default=None),
    metro_station_id: int | None = Query(default=None),
    min_hourly_rate: float | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> VacancyListResponse:
    worker = await _get_worker_or_404(session, user)
    filters = VacancyFilters(
        category_id=category_id,
        metro_station_id=metro_station_id,
        min_hourly_rate=min_hourly_rate,
        page=page,
        limit=limit,
    )
    return await matching_service.list_vacancies_for_worker(session, worker, filters)


@router.get("/{vacancy_id}", response_model=VacancyDetail)
async def get_worker_vacancy(
    vacancy_id: UUID,
    category_id: int | None = Query(default=None),
    metro_station_id: int | None = Query(default=None),
    min_hourly_rate: float | None = Query(default=None, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> VacancyDetail:
    worker = await _get_worker_or_404(session, user)
    filters = VacancyFilters(
        category_id=category_id,
        metro_station_id=metro_station_id,
        min_hourly_rate=min_hourly_rate,
    )
    vacancy = await matching_service.get_vacancy_for_worker(session, worker, vacancy_id, filters)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy
