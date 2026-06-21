from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services import worker_service

router = APIRouter(prefix="/reference", tags=["reference"])


class CategoryRead(BaseModel):
    id: int
    slug: str
    name_ru: str


class MetroStationRead(BaseModel):
    id: int
    name: str
    line_name: str


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: AsyncSession = Depends(get_db_session)) -> list[CategoryRead]:
    categories = await worker_service.list_job_categories(session)
    return [CategoryRead(id=c.id, slug=c.slug, name_ru=c.name_ru) for c in categories]


@router.get("/metro", response_model=list[MetroStationRead])
async def search_metro(
    q: str = Query(default="", max_length=100),
    session: AsyncSession = Depends(get_db_session),
) -> list[MetroStationRead]:
    stations = await worker_service.search_metro_stations(session, q)
    return [MetroStationRead(id=s.id, name=s.name, line_name=s.line_name) for s in stations]
