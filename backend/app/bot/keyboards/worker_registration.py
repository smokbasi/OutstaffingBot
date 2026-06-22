from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.reference.spb_metro import SPB_METRO_LINES


def gender_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мужской", callback_data="gender:male"),
                InlineKeyboardButton(text="Женский", callback_data="gender:female"),
            ],
            [
                InlineKeyboardButton(text="Другое", callback_data="gender:other"),
                InlineKeyboardButton(text="Не указывать", callback_data="gender:prefer_not_say"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reg:cancel")],
        ]
    )


def experience_more_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="exp_more:yes"),
                InlineKeyboardButton(text="Нет", callback_data="exp_more:no"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reg:cancel")],
        ]
    )


def profile_already_complete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Обновить профиль", callback_data="reg:update")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reg:dismiss")],
        ]
    )


def confirm_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="reg:save"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="reg:cancel"),
            ],
        ]
    )


def categories_keyboard(categories: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"cat:{cat_id}")] for cat_id, name in categories]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def metro_lines_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{line.emoji} {line.short_label}", callback_data=f"mline:{line.id}")]
        for line in SPB_METRO_LINES
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def metro_stations_keyboard(stations: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for station_id, name in stations:
        row.append(InlineKeyboardButton(text=name, callback_data=f"mst:{station_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Линии", callback_data="mback:lines")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
