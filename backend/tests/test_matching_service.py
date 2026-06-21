from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models import Gender
from app.schemas.vacancy import VacancyFilters
from app.services.matching_service import (
    effective_category_ids,
    effective_min_rate,
    worker_category_ids,
)


class _Experience:
    def __init__(self, category_id: int) -> None:
        self.category_id = category_id


class _Worker:
    def __init__(
        self,
        *,
        experiences: list[_Experience] | None = None,
        min_hourly_rate: Decimal | None = Decimal("350"),
    ) -> None:
        self.id = uuid4()
        self.age = 25
        self.gender = Gender.male
        self.min_hourly_rate = min_hourly_rate
        self.metro_station_id = 1
        self.metro_radius_km = 0
        self.experiences = experiences or []


def test_worker_category_ids_deduplicates() -> None:
    worker = _Worker(experiences=[_Experience(2), _Experience(2), _Experience(3)])
    assert sorted(worker_category_ids(worker)) == [2, 3]


def test_effective_category_ids_uses_worker_experiences() -> None:
    worker = _Worker(experiences=[_Experience(2), _Experience(5)])
    filters = VacancyFilters()
    assert sorted(effective_category_ids(worker, filters)) == [2, 5]


def test_effective_category_ids_with_valid_filter() -> None:
    worker = _Worker(experiences=[_Experience(2), _Experience(5)])
    filters = VacancyFilters(category_id=2)
    assert effective_category_ids(worker, filters) == [2]


def test_effective_category_ids_rejects_unknown_filter() -> None:
    worker = _Worker(experiences=[_Experience(2)])
    filters = VacancyFilters(category_id=99)
    assert effective_category_ids(worker, filters) == []


def test_effective_category_ids_empty_without_experience() -> None:
    worker = _Worker(experiences=[])
    assert effective_category_ids(worker, VacancyFilters()) == []


def test_effective_min_rate_prefers_filter() -> None:
    worker = _Worker(min_hourly_rate=Decimal("300"))
    filters = VacancyFilters(min_hourly_rate=Decimal("500"))
    assert effective_min_rate(worker, filters) == Decimal("500")


def test_effective_min_rate_uses_worker_default() -> None:
    worker = _Worker(min_hourly_rate=Decimal("300"))
    assert effective_min_rate(worker, VacancyFilters()) == Decimal("300")


def test_effective_min_rate_zero_fallback() -> None:
    worker = _Worker(min_hourly_rate=None)
    assert effective_min_rate(worker, VacancyFilters()) == Decimal(0)
