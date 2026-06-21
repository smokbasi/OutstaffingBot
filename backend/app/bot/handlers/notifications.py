from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.schemas.preferences import WorkerPreferencesUpdate
from app.services import preferences_service, user_service

router = Router(name="notifications")

NOTIFICATIONS_TEXT = (
    "⚙️ <b>Уведомления</b>\n\n"
    "Push о новых вакансиях по вашим категориям, ставке и метро.\n"
    "Подробные фильтры — в Mini App → «Уведомления»."
)


def _notifications_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    toggle_label = "🔕 Выключить push" if enabled else "🔔 Включить push"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_label,
                    callback_data="notif_toggle",
                )
            ]
        ]
    )


async def _render_notifications(message: Message, session: AsyncSession, user: User) -> None:
    try:
        prefs = await preferences_service.get_preferences(session, user)
    except Exception:
        await message.answer("Сначала заполните профиль работника: «📝 Заполнить профиль».")
        return

    status = "включены ✅" if prefs.notifications_enabled else "выключены 🔕"
    text = f"{NOTIFICATIONS_TEXT}\n\nСейчас push <b>{status}</b>."
    await message.answer(text, reply_markup=_notifications_keyboard(prefs.notifications_enabled))


@router.message(F.text == "⚙️ Уведомления")
async def cmd_notifications(message: Message, session: AsyncSession) -> None:
    user = await user_service.get_or_create_by_telegram_id(session, message.from_user.id)
    await _render_notifications(message, session, user)
    await session.commit()


@router.callback_query(F.data == "notif_toggle")
async def toggle_notifications_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_or_create_by_telegram_id(session, callback.from_user.id)
    prefs = await preferences_service.get_preferences(session, user)
    new_enabled = not prefs.notifications_enabled
    await preferences_service.upsert_preferences(
        session,
        user,
        WorkerPreferencesUpdate(notifications_enabled=new_enabled),
    )
    await session.commit()

    status = "включены ✅" if new_enabled else "выключены 🔕"
    text = f"{NOTIFICATIONS_TEXT}\n\nСейчас push <b>{status}</b>."
    await callback.message.edit_text(text, reply_markup=_notifications_keyboard(new_enabled))
    await callback.answer("Сохранено")
