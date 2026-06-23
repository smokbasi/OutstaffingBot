from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.vacancy_search import (
    vacancy_categories_keyboard,
    vacancy_conflict_keyboard,
    vacancy_detail_keyboard,
    vacancy_filters_keyboard,
    vacancy_list_keyboard,
    vacancy_metro_lines_keyboard,
    vacancy_metro_stations_keyboard,
)
from app.bot.states.vacancy_search import VacancySearch
from app.reference.spb_metro import SPB_METRO_LINE_BY_ID
from app.schemas.vacancy import VacancyFilters
from app.services import application_service, matching_service, user_service, worker_service

router = Router(name="vacancy_search")

PAGE_SIZE = 5
FILTERS_PROMPT = (
    "<b>Фильтры поиска</b>\n\n"
    "Категория: {category}\n"
    "Метро: {metro}\n"
    "Мин. ставка: {rate}\n\n"
    "Выберите параметр или нажмите «Применить»."
)


async def _ensure_user(message: Message, session: AsyncSession):
    if message.from_user is None:
        return None
    return await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
    )


async def _ensure_user_from_callback(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user is None:
        return None
    return await user_service.get_or_create_by_telegram_id(
        session,
        callback.from_user.id,
        username=callback.from_user.username,
        language_code=callback.from_user.language_code,
    )


def _format_rate(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0f} ₽/час"


def _format_filters_text(data: dict) -> str:
    return FILTERS_PROMPT.format(
        category=data.get("filter_category_name") or "любая из вашего опыта",
        metro=data.get("filter_metro_name") or "любое",
        rate=_format_rate(data.get("filter_min_rate")),
    )


def _build_filters(data: dict, page: int = 1) -> VacancyFilters:
    return VacancyFilters(
        category_id=data.get("filter_category_id"),
        metro_station_id=data.get("filter_metro_id"),
        min_hourly_rate=data.get("filter_min_rate"),
        page=page,
        limit=PAGE_SIZE,
    )


def _format_vacancy_line(index: int, item) -> str:
    shift_part = "—"
    if item.next_shift_date:
        shift_part = (
            f"{item.next_shift_date.strftime('%d.%m.%Y')} "
            f"{item.next_shift_start.strftime('%H:%M') if item.next_shift_start else ''}"
        ).strip()
    metro = item.metro_station_name or "—"
    return (
        f"{index}. <b>{item.title}</b>\n"
        f"   {item.category_name or '—'} · {metro}\n"
        f"   {_format_rate(item.hourly_rate)} · смена {shift_part}"
    )


async def _show_vacancy_list(
    message: Message,
    session: AsyncSession,
    worker,
    state: FSMContext,
    *,
    page: int = 1,
    edit: bool = False,
) -> None:
    data = await state.get_data()
    filters = _build_filters(data, page=page)
    result = await matching_service.list_vacancies_for_worker(session, worker, filters)
    total_pages = max(1, (result.total + PAGE_SIZE - 1) // PAGE_SIZE)

    if not result.items:
        text = (
            "<b>Вакансии не найдены</b>\n\n"
            "Попробуйте изменить фильтры или проверьте, что в профиле указан опыт работы."
        )
        markup = vacancy_filters_keyboard()
        await state.set_state(VacancySearch.list)
        if edit and message.text:
            await message.edit_text(text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)
        return

    lines = [_format_vacancy_line(idx, item) for idx, item in enumerate(result.items, start=1)]
    text = (
        f"<b>Подходящие вакансии</b> (стр. {page}/{total_pages}, всего {result.total})\n\n"
        + "\n\n".join(lines)
    )
    vacancy_ids = [str(item.id) for item in result.items]
    markup = vacancy_list_keyboard(vacancy_ids, page=page, total_pages=total_pages)
    await state.update_data(vacancy_page=page)
    await state.set_state(VacancySearch.list)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def _start_search(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_user(message, session)
    if user is None:
        return

    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None or not worker.resume_completed:
        await message.answer(
            "Сначала заполните профиль работника: «📝 Заполнить профиль».",
            reply_markup=main_menu_keyboard(),
        )
        return

    if not worker.experiences:
        await message.answer(
            "В профиле нет опыта работы — добавьте категории, чтобы видеть подходящие вакансии.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.clear()
    await state.set_state(VacancySearch.filters)
    await message.answer(_format_filters_text({}), reply_markup=vacancy_filters_keyboard())


@router.message(F.text == "🔍 Найти вакансии")
async def start_vacancy_search(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await _start_search(message, session, state)


@router.callback_query(F.data == "vacfilter:open", StateFilter(VacancySearch))
async def open_filters(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(VacancySearch.filters)
    if callback.message:
        await callback.message.edit_text(
            _format_filters_text(data),
            reply_markup=vacancy_filters_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "vacfilter:open", StateFilter(VacancySearch.list))
@router.callback_query(F.data == "vacfilter:open", StateFilter(VacancySearch.detail))
async def open_filters_from_list(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(VacancySearch.filters)
    if callback.message:
        await callback.message.edit_text(
            _format_filters_text(data),
            reply_markup=vacancy_filters_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "vacfilter:cancel")
async def cancel_vacancy_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Поиск закрыт.")
        await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "vacfilter:reset", StateFilter(VacancySearch))
async def reset_filters(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(
        filter_category_id=None,
        filter_category_name=None,
        filter_metro_id=None,
        filter_metro_name=None,
        filter_min_rate=None,
    )
    data = await state.get_data()
    if callback.message:
        await callback.message.edit_text(
            _format_filters_text(data),
            reply_markup=vacancy_filters_keyboard(),
        )
    await callback.answer("Фильтры сброшены")


@router.callback_query(F.data == "vacfilter:category", StateFilter(VacancySearch))
async def filter_category_prompt(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    categories = [(exp.category_id, exp.category.name_ru) for exp in worker.experiences if exp.category]
    if callback.message:
        await callback.message.edit_text(
            "Выберите <b>категорию</b>:",
            reply_markup=vacancy_categories_keyboard(categories),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("vaccat:"), StateFilter(VacancySearch))
async def filter_category_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None:
        return
    category_id = int(callback.data.split(":", 1)[1])
    categories = await worker_service.list_job_categories(session)
    category_name = next((cat.name_ru for cat in categories if cat.id == category_id), str(category_id))
    await state.update_data(filter_category_id=category_id, filter_category_name=category_name)
    data = await state.get_data()
    if callback.message:
        await callback.message.edit_text(
            _format_filters_text(data),
            reply_markup=vacancy_filters_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "vacfilter:metro", StateFilter(VacancySearch))
async def filter_metro_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Выберите <b>линию метро</b>:",
            reply_markup=vacancy_metro_lines_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "vacmback:lines", StateFilter(VacancySearch))
async def filter_metro_back_to_lines(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Выберите <b>линию метро</b>:",
            reply_markup=vacancy_metro_lines_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("vacmline:"), StateFilter(VacancySearch))
async def filter_metro_line(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None:
        return
    line_id = int(callback.data.split(":", 1)[1])
    line = SPB_METRO_LINE_BY_ID.get(line_id)
    if line is None:
        await callback.answer("Линия не найдена", show_alert=True)
        return
    stations = await worker_service.list_metro_stations_by_line_name(session, line.name)
    if callback.message:
        await callback.message.edit_text(
            f"Выберите <b>станцию</b> ({line.emoji} {line.name}):",
            reply_markup=vacancy_metro_stations_keyboard([(station.id, station.name) for station in stations]),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("vacmst:"), StateFilter(VacancySearch))
async def filter_metro_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None:
        return
    station_id = int(callback.data.split(":", 1)[1])
    station = await worker_service.get_metro_station_by_id(session, station_id)
    if station is None:
        await callback.answer("Станция не найдена", show_alert=True)
        return
    await state.update_data(filter_metro_id=station.id, filter_metro_name=station.name)
    data = await state.get_data()
    if callback.message:
        await callback.message.edit_text(
            _format_filters_text(data),
            reply_markup=vacancy_filters_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "vacfilter:rate", StateFilter(VacancySearch))
async def filter_rate_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(VacancySearch.filters)
    if callback.message:
        await callback.message.edit_text(
            "Введите <b>минимальную ставку</b> (₽/час, только число):",
            reply_markup=vacancy_filters_keyboard(),
        )
    await callback.answer()


@router.message(StateFilter(VacancySearch.filters), F.text)
async def filter_rate_input(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().replace(",", ".")
    if text.startswith("🔧") or text.startswith("❌"):
        return
    try:
        rate = Decimal(text)
        if rate < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректную ставку (число ≥ 0).")
        return

    await state.update_data(filter_min_rate=rate)
    data = await state.get_data()
    await message.answer(_format_filters_text(data), reply_markup=vacancy_filters_keyboard())


@router.callback_query(F.data == "vacfilter:apply", StateFilter(VacancySearch))
async def apply_filters(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_user_from_callback(callback, session)
    if user is None or callback.message is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    await _show_vacancy_list(callback.message, session, worker, state, page=1, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("vacpage:"), StateFilter(VacancySearch.list))
async def vacancy_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    page = int(callback.data.split(":", 1)[1])
    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    await _show_vacancy_list(callback.message, session, worker, state, page=page, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("vacancy:"), StateFilter(VacancySearch.list))
async def vacancy_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    from uuid import UUID

    job_id = UUID(callback.data.split(":", 1)[1])
    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    data = await state.get_data()
    filters = _build_filters(data, page=data.get("vacancy_page", 1))
    vacancy = await matching_service.get_vacancy_for_worker(session, worker, job_id, filters)
    if vacancy is None:
        await callback.answer("Вакансия недоступна", show_alert=True)
        return

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
        f"{vacancy.description}\n\n"
        f"<b>Смены:</b>\n{shifts_text}\n\n"
        "Выберите смену для отклика:"
    )
    await state.update_data(current_vacancy_id=str(vacancy.id))
    await state.set_state(VacancySearch.detail)
    slot_payload = [
        {
            "id": str(slot.id),
            "shift_date": slot.shift_date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
        }
        for slot in vacancy.shift_slots
    ]
    await callback.message.edit_text(
        text,
        reply_markup=vacancy_detail_keyboard(str(vacancy.id), slot_payload),
    )
    await callback.answer()


@router.callback_query(F.data == "vacback:list", StateFilter(VacancySearch.detail))
async def back_to_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None:
        return
    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    data = await state.get_data()
    page = data.get("vacancy_page", 1)
    await _show_vacancy_list(callback.message, session, worker, state, page=page, edit=True)
    await callback.answer()


async def _render_vacancy_detail(
    message: Message,
    session: AsyncSession,
    worker,
    state: FSMContext,
    job_id,
) -> None:
    data = await state.get_data()
    filters = _build_filters(data, page=data.get("vacancy_page", 1))
    vacancy = await matching_service.get_vacancy_for_worker(session, worker, job_id, filters)
    if vacancy is None:
        await message.edit_text("Вакансия недоступна.")
        return

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
        f"{vacancy.description}\n\n"
        f"<b>Смены:</b>\n{shifts_text}\n\n"
        "Выберите смену для отклика:"
    )
    await state.update_data(current_vacancy_id=str(vacancy.id))
    await state.set_state(VacancySearch.detail)
    slot_payload = [
        {
            "id": str(slot.id),
            "shift_date": slot.shift_date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
        }
        for slot in vacancy.shift_slots
    ]
    await message.edit_text(
        text,
        reply_markup=vacancy_detail_keyboard(str(vacancy.id), slot_payload),
    )


@router.callback_query(F.data == "vacback:detail", StateFilter(VacancySearch.conflict))
async def back_to_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.message is None:
        return
    from uuid import UUID

    data = await state.get_data()
    vacancy_id = data.get("current_vacancy_id")
    if not vacancy_id:
        await callback.answer("Вакансия не найдена", show_alert=True)
        return

    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    await _render_vacancy_detail(callback.message, session, worker, state, UUID(vacancy_id))
    await callback.answer()


@router.callback_query(F.data.startswith("vacslot:"), StateFilter(VacancySearch.detail))
async def apply_to_shift(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    from uuid import UUID

    slot_id = UUID(callback.data.split(":", 1)[1])
    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    try:
        result = await application_service.apply_to_shift(session, worker, slot_id)
        await session.commit()
    except application_service.ShiftConflictError as exc:
        conflict = exc.conflicting_application
        slot = conflict.shift_slot
        await state.update_data(pending_slot_id=str(slot_id))
        await state.set_state(VacancySearch.conflict)
        text = (
            f"⚠️ <b>Конфликт смен</b>\n\n"
            f"У вас уже есть смена {slot.shift_date.strftime('%d.%m.%Y')} "
            f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')} "
            f"({conflict.job_request.title if conflict.job_request else '—'}).\n\n"
            "Отмените её, чтобы откликнуться на новую."
        )
        await callback.message.edit_text(
            text,
            reply_markup=vacancy_conflict_keyboard(str(conflict.id), str(slot_id)),
        )
        await callback.answer()
        return
    except application_service.AlreadyAppliedError:
        await callback.answer("Вы уже откликались на эту смену", show_alert=True)
        return
    except application_service.SlotUnavailableError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except application_service.ApplicationNotFoundError:
        await callback.answer("Смена не найдена", show_alert=True)
        return
    except application_service.WorkerBannedError:
        await callback.answer("Аккаунт заблокирован", show_alert=True)
        return
    except application_service.WorkerNotVerifiedError:
        await callback.answer(
            "Профиль не верифицирован — дождитесь подтверждения администратором",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        f"✅ <b>Отклик отправлен!</b>\n\n"
        f"{result.job_title}\n"
        f"{result.shift_date.strftime('%d.%m.%Y')} "
        f"{result.start_time.strftime('%H:%M')}–{result.end_time.strftime('%H:%M')}\n\n"
        "Статус: на рассмотрении.",
    )
    await callback.answer("Отклик отправлен")


@router.callback_query(F.data.startswith("vacapply:swap:"), StateFilter(VacancySearch.conflict))
async def apply_with_cancel_previous(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    from uuid import UUID

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    conflicting_id = UUID(parts[2])
    slot_id = UUID(parts[3])

    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        return
    worker = await worker_service.get_worker_by_user_id(session, user.id)
    if worker is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    try:
        result = await application_service.apply_to_shift(
            session,
            worker,
            slot_id,
            cancel_conflicting_id=conflicting_id,
        )
        await session.commit()
    except application_service.ShiftConflictError:
        await callback.answer("Конфликт не удалось разрешить", show_alert=True)
        return
    except (application_service.SlotUnavailableError, application_service.AlreadyAppliedError) as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except application_service.WorkerBannedError:
        await callback.answer("Аккаунт заблокирован", show_alert=True)
        return
    except application_service.WorkerNotVerifiedError:
        await callback.answer(
            "Профиль не верифицирован — дождитесь подтверждения администратором",
            show_alert=True,
        )
        return

    await state.set_state(VacancySearch.detail)
    await callback.message.edit_text(
        f"✅ <b>Отклик отправлен!</b>\n\n"
        f"Предыдущая смена отменена.\n\n"
        f"{result.job_title}\n"
        f"{result.shift_date.strftime('%d.%m.%Y')} "
        f"{result.start_time.strftime('%H:%M')}–{result.end_time.strftime('%H:%M')}\n\n"
        "Статус: на рассмотрении.",
    )
    await callback.answer("Отклик отправлен")
