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


def vacancy_detail_keyboard(vacancy_id: str, shift_slots: list[dict] | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if shift_slots:
        for slot in shift_slots:
            slot_id = slot["id"]
            date_str = slot.get("shift_date", "")
            if hasattr(date_str, "strftime"):
                date_str = date_str.strftime("%d.%m")
            start = slot.get("start_time", "")
            end = slot.get("end_time", "")
            if hasattr(start, "strftime"):
                start = start.strftime("%H:%M")
            if hasattr(end, "strftime"):
                end = end.strftime("%H:%M")
            label = f"✅ Откликнуться · {date_str} {start}–{end}"
            rows.append([InlineKeyboardButton(text=label, callback_data=f"vacslot:{slot_id}")])
    rows.append([InlineKeyboardButton(text="◀️ К списку", callback_data="vacback:list")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="vacfilter:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vacancy_conflict_keyboard(conflicting_id: str, new_slot_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Отменить предыдущую и откликнуться",
                    callback_data=f"vacapply:swap:{conflicting_id}:{new_slot_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="vacback:detail")],
        ]
    )


def my_applications_keyboard(application_ids: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for app_id in application_ids:
        rows.append(
            [InlineKeyboardButton(text="❌ Отменить отклик", callback_data=f"vaccancel:{app_id}")]
        )
    rows.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="vacapps:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
