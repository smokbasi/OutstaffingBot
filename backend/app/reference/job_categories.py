"""Job categories reference — display order matters for bot keyboard and API."""

from typing import NamedTuple


class CategorySeed(NamedTuple):
    slug: str
    name_ru: str


# Фасовщик — первая категория (склад / логистика); порядок задаётся явно, не по алфавиту.
JOB_CATEGORIES: tuple[CategorySeed, ...] = (
    CategorySeed("packer", "Фасовщик"),
    CategorySeed("waiter", "Официант"),
    CategorySeed("bartender", "Бармен"),
    CategorySeed("cashier", "Кассир"),
    CategorySeed("loader", "Грузчик"),
    CategorySeed("courier", "Курьер"),
    CategorySeed("promo", "Промоутер"),
    CategorySeed("cleaner", "Уборщик"),
    CategorySeed("cook_helper", "Помощник повара"),
    CategorySeed("warehouse", "Складской работник"),
    CategorySeed("event_staff", "Персонал мероприятий"),
    CategorySeed("security", "Охранник"),
    CategorySeed("driver", "Водитель"),
    CategorySeed("other", "Другое"),
)

_CATEGORY_ORDER: dict[str, int] = {item.slug: index for index, item in enumerate(JOB_CATEGORIES)}


def sort_job_categories(categories: list) -> list:
    return sorted(categories, key=lambda category: _CATEGORY_ORDER.get(category.slug, len(JOB_CATEGORIES)))
