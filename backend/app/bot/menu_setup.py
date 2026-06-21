"""Синяя кнопка Mini App в меню Telegram (слева от поля ввода)."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MINI_APP_MENU_TEXT = "Открыть приложение"


def mini_app_menu_button() -> MenuButtonWebApp | MenuButtonCommands:
    settings = get_settings()
    if settings.mini_app_url:
        return MenuButtonWebApp(
            text=MINI_APP_MENU_TEXT,
            web_app=WebAppInfo(url=settings.mini_app_url),
        )
    return MenuButtonCommands()


async def setup_default_mini_app_menu(bot: Bot) -> None:
    """Глобальная кнопка Mini App — для всех чатов и пользователей."""
    await refresh_user_mini_app_menu(bot)


async def refresh_user_mini_app_menu(bot: Bot, chat_id: int | None = None) -> bool:
    """Обновить синюю кнопку Mini App (глобально или для одного чата)."""
    settings = get_settings()
    if not settings.mini_app_url:
        return False
    try:
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=mini_app_menu_button(),
        )
        scope = f"chat_id={chat_id}" if chat_id is not None else "default/global"
        logger.info("Mini App menu button refreshed (%s)", scope)
        return True
    except Exception as exc:
        logger.warning("Mini App menu button refresh failed: %s", exc)
        return False
