"""Seed metro_stations — MVP placeholder set (full Moscow import in Phase 3+)."""

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.models import MetroStation  # noqa: E402

DATA_FILE = Path(__file__).resolve().parent / "data" / "metro_stations_sample.json"

# Minimal inline fallback if JSON is missing
DEFAULT_STATIONS = [
    {"name": "Сокольники", "line_name": "Сокольническая", "lat": "55.7889", "lon": "37.6803"},
    {"name": "Красносельская", "line_name": "Сокольническая", "lat": "55.7724", "lon": "37.6650"},
    {"name": "Комсомольская", "line_name": "Сокольническая", "lat": "55.7753", "lon": "37.6556"},
    {"name": "Курская", "line_name": "Кольцевая", "lat": "55.7586", "lon": "37.6593"},
    {"name": "Таганская", "line_name": "Кольцевая", "lat": "55.7424", "lon": "37.6533"},
    {"name": "Павелецкая", "line_name": "Кольцевая", "lat": "55.7315", "lon": "37.6363"},
    {"name": "Добрынинская", "line_name": "Кольцевая", "lat": "55.7289", "lon": "37.6225"},
    {"name": "Киевская", "line_name": "Кольцевая", "lat": "55.7436", "lon": "37.5656"},
]


def load_stations() -> list[dict[str, str]]:
    if DATA_FILE.exists():
        with DATA_FILE.open(encoding="utf-8") as file:
            return json.load(file)
    return DEFAULT_STATIONS


async def seed_metro(session: AsyncSession) -> int:
    inserted = 0
    for station in load_stations():
        exists = await session.scalar(
            select(MetroStation.id).where(
                MetroStation.name == station["name"],
                MetroStation.line_name == station["line_name"],
            )
        )
        if exists:
            continue
        session.add(
            MetroStation(
                name=station["name"],
                line_name=station["line_name"],
                lat=Decimal(station["lat"]) if station.get("lat") else None,
                lon=Decimal(station["lon"]) if station.get("lon") else None,
                is_active=True,
            )
        )
        inserted += 1
    await session.commit()
    return inserted


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        count = await seed_metro(session)
        total = len(load_stations())
        print(f"Seeded {count} metro stations ({total} defined in data source).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
