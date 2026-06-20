from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.core.config import get_settings


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    settings = get_settings()
    rows = [
        [KeyboardButton(text="👷 Работник"), KeyboardButton(text="🏢 Работодатель")],
    ]
    if settings.mini_app_url:
        rows.append(
            [KeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=settings.mini_app_url))]
        )
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
