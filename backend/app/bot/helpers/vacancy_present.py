from decimal import Decimal
from uuid import UUID

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.vacancy_search import vacancy_detail_keyboard
from app.bot.states.vacancy_search import VacancySearch
from app.db.models import Worker
from app.schemas.vacancy import VacancyDetail
from app.services import matching_service


def _format_rate(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0f} ₽/час"


def _format_vacancy_detail_text(vacancy: VacancyDetail) -> str:
    shift_lines = []
    for slot in vacancy.shift_slots:
        shift_lines.append(
            f"• {slot.shift_date.strftime('%d.%m.%Y')} "
            f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')} "
            f"(свободно {slot.slots_total - slot.slots_filled}/{slot.slots_total})"
        )
    shifts_text = "\n".join(shift_lines) if shift_lines else "—"

    text = (
        f"<b>{vacancy.title}</b>\n"
        f"{vacancy.category_name or '—'} · {vacancy.metro_station_name or '—'}\n"
        f"{_format_rate(vacancy.hourly_rate)}\n\n"
        f"{vacancy.description}"
    )
    if vacancy.dress_code:
        text += f"\nДресс-код: {vacancy.dress_code}"
    if vacancy.includes_lunch:
        text += "\n🍽 Обед включён"

    text += (
        f"\n\n<b>Смены:</b>\n"
        f"{shifts_text}\n\n"
        "Выберите смену для отклика:"
    )
    return text


def _slot_payload(vacancy: VacancyDetail) -> list[dict]:
    return [
        {
            "id": str(slot.id),
            "shift_date": slot.shift_date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
        }
        for slot in vacancy.shift_slots
    ]


async def send_job_vacancy_for_apply_to_chat(
    bot: Bot,
    chat_id: int,
    session: AsyncSession,
    worker: Worker,
    state: FSMContext,
    job_id: UUID,
) -> bool:
    """Send job card with shift apply buttons to a chat. Returns False if job unavailable."""
    vacancy = await matching_service.get_vacancy_detail_by_id(session, job_id)
    if vacancy is None:
        return False

    if not vacancy.shift_slots:
        await bot.send_message(chat_id, "На эту вакансию нет доступных смен для отклика.")
        return False

    await state.update_data(current_vacancy_id=str(vacancy.id), from_job_deep_link=True)
    await state.set_state(VacancySearch.detail)
    await bot.send_message(
        chat_id,
        _format_vacancy_detail_text(vacancy),
        reply_markup=vacancy_detail_keyboard(
            str(vacancy.id),
            _slot_payload(vacancy),
            from_deep_link=True,
        ),
    )
    return True


async def send_job_vacancy_for_apply(
    message: Message,
    session: AsyncSession,
    worker: Worker,
    state: FSMContext,
    job_id: UUID,
) -> bool:
    """Send job card with shift apply buttons. Returns False if job unavailable."""
    if message.bot is None:
        return False
    return await send_job_vacancy_for_apply_to_chat(
        message.bot,
        message.chat.id,
        session,
        worker,
        state,
        job_id,
    )
