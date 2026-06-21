"""Уведомление админов о перезапуске бота после деплоя."""
from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.core.config import Settings, get_settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "bot:update_announcement:"
DEFAULT_RELEASE_NOTES = "Обновление без описания"
RELEASE_NOTES_FILENAME = "RELEASE_NOTES.txt"


def format_update_message(release_notes: str) -> str:
    notes = release_notes.strip() or DEFAULT_RELEASE_NOTES
    return f"Бот обновлен!\n({notes})"


def resolve_release_notes(settings: Settings) -> str:
    if settings.bot_release_notes.strip():
        return settings.bot_release_notes.strip()

    notes_path = Path(settings.release_notes_file)
    if notes_path.is_file():
        return notes_path.read_text(encoding="utf-8").strip()

    return DEFAULT_RELEASE_NOTES


def _redis_key(chat_id: int) -> str:
    return f"{REDIS_KEY_PREFIX}{chat_id}"


async def _delete_previous_announcement(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info("Deleted previous update announcement chat_id=%s message_id=%s", chat_id, message_id)
    except TelegramBadRequest as exc:
        logger.debug(
            "Previous update announcement not deleted chat_id=%s message_id=%s: %s",
            chat_id,
            message_id,
            exc,
        )
    except TelegramForbiddenError as exc:
        logger.warning(
            "Cannot delete previous update announcement chat_id=%s: %s",
            chat_id,
            exc,
        )


async def _send_update_announcement(bot: Bot, chat_id: int, text: str) -> Message | None:
    try:
        return await bot.send_message(chat_id=chat_id, text=text, reply_markup=main_menu_keyboard())
    except TelegramForbiddenError as exc:
        logger.warning("Cannot send update announcement chat_id=%s: %s", chat_id, exc)
        return None


async def announce_bot_update(bot: Bot) -> None:
    settings = get_settings()
    recipient_ids = settings.admin_telegram_ids
    if not recipient_ids:
        logger.info("No ADMIN_TELEGRAM_IDS configured — skipping bot update announcement")
        return

    release_notes = resolve_release_notes(settings)
    text = format_update_message(release_notes)
    redis_client = get_redis()

    for chat_id in recipient_ids:
        stored_message_id = await redis_client.get(_redis_key(chat_id))
        if stored_message_id:
            await _delete_previous_announcement(bot, chat_id, int(stored_message_id))

        message = await _send_update_announcement(bot, chat_id, text)
        if message is not None:
            await redis_client.set(_redis_key(chat_id), str(message.message_id))
            logger.info("Sent bot update announcement chat_id=%s message_id=%s", chat_id, message.message_id)
