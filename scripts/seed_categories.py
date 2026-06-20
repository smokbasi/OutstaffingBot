"""Seed job_categories from PLAN.md MVP reference."""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.models import JobCategory  # noqa: E402

CATEGORIES = [
    ("waiter", "Официант"),
    ("bartender", "Бармен"),
    ("cashier", "Кассир"),
    ("loader", "Грузчик"),
    ("courier", "Курьер"),
    ("promo", "Промоутер"),
    ("cleaner", "Уборщик"),
    ("cook_helper", "Помощник повара"),
    ("warehouse", "Складской работник"),
    ("event_staff", "Персонал мероприятий"),
    ("security", "Охранник"),
    ("driver", "Водитель"),
    ("other", "Другое"),
]


async def seed_categories(session: AsyncSession) -> int:
    inserted = 0
    for slug, name_ru in CATEGORIES:
        exists = await session.scalar(select(JobCategory.id).where(JobCategory.slug == slug))
        if exists:
            continue
        session.add(JobCategory(slug=slug, name_ru=name_ru, is_active=True))
        inserted += 1
    await session.commit()
    return inserted


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        count = await seed_categories(session)
        print(f"Seeded {count} job categories ({len(CATEGORIES)} total defined).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
