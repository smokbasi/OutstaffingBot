from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👷 Работник"), KeyboardButton(text="🏢 Работодатель")],
            [KeyboardButton(text="🔍 Найти вакансии")],
            [KeyboardButton(text="📝 Заполнить профиль")],
        ],
        resize_keyboard=True,
    )
