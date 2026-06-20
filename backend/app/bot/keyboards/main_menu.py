from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👷 Работник"), KeyboardButton(text="🏢 Работодатель")],
        ],
        resize_keyboard=True,
    )
