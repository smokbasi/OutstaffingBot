from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.validators.job_request import format_shift_date
from app.reference.spb_metro import SPB_METRO_LINES


def cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="❌ Отмена", callback_data="job:cancel")


def employer_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать заявку", callback_data="job:new")],
            [cancel_button()],
        ]
    )


def categories_keyboard(categories: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"jobcat:{cat_id}")] for cat_id, name in categories]
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def metro_lines_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{line.emoji} {line.short_label}", callback_data=f"jobmline:{line.id}")]
        for line in SPB_METRO_LINES
    ]
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def metro_stations_keyboard(stations: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for station_id, name in stations:
        row.append(InlineKeyboardButton(text=name, callback_data=f"jobmst:{station_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Линии", callback_data="jobmback:lines")])
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shift_dates_keyboard(dates: list[date], selected: set[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for shift_date in dates:
        iso = shift_date.isoformat()
        prefix = "✅ " if iso in selected else ""
        row.append(
            InlineKeyboardButton(
                text=f"{prefix}{format_shift_date(shift_date)}",
                callback_data=f"jobdate:{iso}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✅ Готово с датами", callback_data="jobdate:done")])
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def optional_fields_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📍 Адрес", callback_data="jobopt:address")],
            [InlineKeyboardButton(text="📋 Мин. опыт (мес.)", callback_data="jobopt:experience")],
            [InlineKeyboardButton(text="👤 Пол работника", callback_data="jobopt:gender")],
            [InlineKeyboardButton(text="🎂 Возраст (мин/макс)", callback_data="jobopt:age")],
            [InlineKeyboardButton(text="👔 Дресс-код", callback_data="jobopt:dress")],
            [InlineKeyboardButton(text="📞 Контакт", callback_data="jobopt:contact")],
            [InlineKeyboardButton(text="🍽 Обед включён", callback_data="jobopt:lunch")],
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="jobopt:skip"),
                InlineKeyboardButton(text="✅ Готово", callback_data="jobopt:done"),
            ],
            [cancel_button()],
        ]
    )


def required_gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Любой", callback_data="jobgender:any"),
                InlineKeyboardButton(text="Мужской", callback_data="jobgender:male"),
                InlineKeyboardButton(text="Женский", callback_data="jobgender:female"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="jobopt:back")],
            [cancel_button()],
        ]
    )


def post_to_groups_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="jobgroups:yes"),
                InlineKeyboardButton(text="Нет", callback_data="jobgroups:no"),
            ],
            [cancel_button()],
        ]
    )


def lunch_included_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="joblunch:yes"),
                InlineKeyboardButton(text="Нет", callback_data="joblunch:no"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="joblunch:back")],
            [cancel_button()],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💾 Черновик", callback_data="jobconfirm:draft"),
                InlineKeyboardButton(text="🚀 Опубликовать", callback_data="jobconfirm:publish"),
            ],
            [cancel_button()],
        ]
    )
