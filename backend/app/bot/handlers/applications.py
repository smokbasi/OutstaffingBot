from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.vacancy_search import my_applications_keyboard
from app.schemas.application import format_application_status
from app.services import application_service, user_service, worker_service

router = Router(name="applications")


def _format_shift_line_from_read(item) -> str:
    date_str = item.shift_date.strftime("%d.%m.%Y")
    time_str = f"{item.start_time.strftime('%H:%M')}–{item.end_time.strftime('%H:%M')}"
    status = format_application_status(item.status)
    return f"• <b>{item.job_title}</b>\n  {date_str} {time_str}\n  Статус: {status}"


async def _show_my_applications(message: Message, session: AsyncSession, *, edit: bool = False) -> None:
    if message.from_user is None:
        return
    user = await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
    )
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        text = "Сначала заполните профиль работника: «📝 Заполнить профиль»."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=main_menu_keyboard())
        return

    result = await application_service.list_my_applications(session, worker)
    if not result.items:
        text = "<b>Мои отклики</b>\n\nУ вас пока нет активных откликов."
        if edit:
            await message.edit_text(text, reply_markup=my_applications_keyboard([]))
        else:
            await message.answer(text, reply_markup=main_menu_keyboard())
        return

    lines = [_format_shift_line_from_read(item) for item in result.items]
    text = "<b>Мои отклики</b>\n\n" + "\n\n".join(lines)
    app_ids = [str(item.id) for item in result.items]
    markup = my_applications_keyboard(app_ids)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(F.text == "📋 Мои отклики")
async def my_applications_command(message: Message, session: AsyncSession) -> None:
    await _show_my_applications(message, session)


@router.callback_query(F.data == "vacapps:close")
async def close_applications(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text("Главное меню:")
        await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("vaccancel:"))
async def cancel_application_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        return
    app_id = UUID(callback.data.split(":", 1)[1])
    user = await user_service.get_or_create_by_telegram_id(
        session,
        callback.from_user.id,
        username=callback.from_user.username,
        language_code=callback.from_user.language_code,
    )
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    try:
        await application_service.cancel_application(session, worker, app_id)
        await session.commit()
    except application_service.ApplicationNotFoundError:
        await callback.answer("Отклик не найден", show_alert=True)
        return
    except application_service.ApplicationNotCancellableError:
        await callback.answer("Этот отклик нельзя отменить", show_alert=True)
        return

    await callback.answer("Отклик отменён")
    await _show_my_applications(callback.message, session, edit=True)
