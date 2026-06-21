from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def vacancy_categories_keyboard(categories: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"vaccat:{cat_id}")] for cat_id, name in categories]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="vacfilter:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vacancy_metro_lines_keyboard() -> InlineKeyboardMarkup:
    from app.reference.spb_metro import SPB_METRO_LINES

    rows = [
        [InlineKeyboardButton(text=f"{line.emoji} {line.short_label}", callback_data=f"vacmline:{line.id}")]
        for line in SPB_METRO_LINES
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="vacfilter:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vacancy_metro_stations_keyboard(stations: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for station_id, name in stations:
        row.append(InlineKeyboardButton(text=name, callback_data=f"vacmst:{station_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Линии", callback_data="vacmback:lines")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="vacfilter:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vacancy_filters_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📂 Категория", callback_data="vacfilter:category")],
            [InlineKeyboardButton(text="🚇 Метро", callback_data="vacfilter:metro")],
            [InlineKeyboardButton(text="💰 Мин. ставка", callback_data="vacfilter:rate")],
            [
                InlineKeyboardButton(text="✅ Применить", callback_data="vacfilter:apply"),
                InlineKeyboardButton(text="🔄 Сбросить", callback_data="vacfilter:reset"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="vacfilter:cancel")],
        ]
    )


def vacancy_list_keyboard(
    vacancy_ids: list[str],
    *,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, vacancy_id in enumerate(vacancy_ids, start=1):
        rows.append([InlineKeyboardButton(text=f"📋 Вакансия {idx}", callback_data=f"vacancy:{vacancy_id}")])

    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"vacpage:{page - 1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"vacpage:{page + 1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="🔧 Фильтры", callback_data="vacfilter:open")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="vacfilter:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vacancy_detail_keyboard(vacancy_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К списку", callback_data="vacback:list")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="vacfilter:cancel")],
        ]
    )
