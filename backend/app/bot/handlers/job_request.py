from datetime import date, time
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.job_request import (
    categories_keyboard,
    confirm_keyboard,
    employer_menu_keyboard,
    metro_lines_keyboard,
    metro_stations_keyboard,
    optional_fields_keyboard,
    post_to_groups_keyboard,
    required_gender_keyboard,
    shift_dates_keyboard,
)
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.job_request import EmployerOnboarding, JobRequestCreation
from app.bot.validators.job_request import (
    format_shift_date,
    parse_hourly_rate,
    parse_optional_int,
    parse_shift_time,
    parse_workers_needed,
    upcoming_shift_dates,
    validate_shift_times,
)
from app.db.models import JobRequestStatus, RequiredGender
from app.reference.job_request_status import job_request_status_label
from app.reference.spb_metro import SPB_METRO_LINE_BY_ID
from app.schemas.employer import EmployerProfileUpdate
from app.schemas.job_request import JobRequestCreate, JobRequestUpdate, ShiftSlotCreate
from app.services import employer_service, job_service, user_service, worker_service

router = Router(name="job_request")

REQUIRED_GENDER_LABELS = {
    RequiredGender.any: "Любой",
    RequiredGender.male: "Мужской",
    RequiredGender.female: "Женский",
}

GENDER_CALLBACK_MAP = {
    "jobgender:any": RequiredGender.any,
    "jobgender:male": RequiredGender.male,
    "jobgender:female": RequiredGender.female,
}

COMPANY_NAME_PROMPT = "Введите <b>название компании</b>:"
CATEGORY_PROMPT = "Выберите <b>категорию</b> вакансии:"
TITLE_PROMPT = "Введите <b>название</b> заявки (до 200 символов):"
DESCRIPTION_PROMPT = "Введите <b>описание</b> заявки:"
METRO_LINES_PROMPT = "Выберите <b>линию метро</b>:"
HOURLY_RATE_PROMPT = "Укажите <b>почасовую ставку</b> (₽/час, только число):"
WORKERS_NEEDED_PROMPT = "Сколько <b>работников</b> нужно на смену (1–100)?"
SHIFT_DATES_PROMPT = "Выберите <b>даты смен</b> (можно несколько), затем нажмите «Готово»:"
POST_TO_GROUPS_PROMPT = "Публиковать заявку в <b>Telegram-группы</b>?"


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


def _format_shift_slots(data: dict) -> str:
    slots = data.get("shift_slots") or []
    if not slots:
        return "—"
    lines = []
    for slot in slots:
        shift_date = date.fromisoformat(slot["shift_date"])
        lines.append(
            f"• {format_shift_date(shift_date)}: {slot['start_time']}–{slot['end_time']}"
        )
    return "\n".join(lines)


def _format_job_summary(data: dict) -> str:
    lines = [
        "<b>Заявка работодателя</b>",
        f"Категория: {data.get('category_name', '—')}",
        f"Название: {data.get('title', '—')}",
        f"Описание: {data.get('description', '—')}",
        f"Метро: {data.get('metro_name', '—')}",
        f"Ставка: {data.get('hourly_rate', '—')} ₽/час",
        f"Работников: {data.get('workers_needed', '—')}",
        "",
        "<b>Смены:</b>",
        _format_shift_slots(data),
    ]
    if data.get("address"):
        lines.append(f"Адрес: {data['address']}")
    if data.get("min_experience_months") is not None:
        lines.append(f"Мин. опыт: {data['min_experience_months']} мес.")
    if data.get("required_gender"):
        lines.append(f"Пол: {REQUIRED_GENDER_LABELS.get(data['required_gender'], '—')}")
    if data.get("min_age") is not None or data.get("max_age") is not None:
        lines.append(f"Возраст: {data.get('min_age', '—')}–{data.get('max_age', '—')}")
    if data.get("dress_code"):
        lines.append(f"Дресс-код: {data['dress_code']}")
    if data.get("contact_info"):
        lines.append(f"Контакт: {data['contact_info']}")
    if "post_to_groups" in data:
        lines.append(f"В группы: {'да' if data['post_to_groups'] else 'нет'}")
    return "\n".join(lines)


def _summary_text(data: dict, tail: str) -> str:
    return f"{_format_job_summary(data)}\n\n{tail}"


async def _start_summary_message(
    message: Message,
    state: FSMContext,
    tail: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    sent = await message.answer(_summary_text(data, tail), reply_markup=reply_markup)
    await state.update_data(summary_chat_id=sent.chat.id, summary_message_id=sent.message_id)


async def _update_summary_message(
    bot: Bot,
    state: FSMContext,
    tail: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    chat_id = data.get("summary_chat_id")
    message_id = data.get("summary_message_id")
    if chat_id is None or message_id is None:
        return
    try:
        await bot.edit_message_text(
            _summary_text(data, tail),
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )
    except Exception:
        return


async def _delete_message_safe(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        return


async def _delete_user_message(message: Message) -> None:
    await _delete_message_safe(message.bot, message.chat.id, message.message_id)


async def _clear_job_fsm(message: Message | CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    bot = message.bot if isinstance(message, Message) else message.bot
    if data.get("summary_chat_id") and data.get("summary_message_id"):
        await _delete_message_safe(bot, data["summary_chat_id"], data["summary_message_id"])
    await state.clear()


async def _begin_job_creation(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await state.set_state(JobRequestCreation.category)
    categories = await worker_service.list_job_categories(session)
    keyboard = categories_keyboard([(category.id, category.name_ru) for category in categories])
    await _start_summary_message(message, state, CATEGORY_PROMPT, keyboard)


async def _show_employer_menu(message: Message, company_name: str) -> None:
    await message.answer(
        f"<b>Режим работодателя</b>\nКомпания: {company_name}\n\n"
        "Создайте новую заявку или вернитесь в главное меню.",
        reply_markup=employer_menu_keyboard(),
    )


@router.message(F.text == "🏢 Работодатель")
async def select_employer(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_user(message, session)
    if user is None:
        return

    profile = await employer_service.get_employer_profile(session, user)
    if profile is None:
        await state.clear()
        await state.set_state(EmployerOnboarding.company_name)
        await message.answer(
            "Добро пожаловать! Сначала укажите компанию.\n\n" + COMPANY_NAME_PROMPT,
            reply_markup=main_menu_keyboard(),
        )
        return

    await _show_employer_menu(message, profile.company_name)


@router.message(EmployerOnboarding.company_name)
async def process_company_name(message: Message, session: AsyncSession, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 1 or len(name) > 200:
        await message.answer("Название компании — от 1 до 200 символов.\n\n" + COMPANY_NAME_PROMPT)
        return

    user = await _ensure_user(message, session)
    if user is None:
        return

    profile = await employer_service.upsert_employer_profile(
        session,
        user,
        EmployerProfileUpdate(company_name=name),
    )
    await state.clear()
    await message.answer(f"✅ Компания «{profile.company_name}» сохранена.")
    await _show_employer_menu(message, profile.company_name)


@router.callback_query(F.data == "job:new")
async def start_job_creation_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user = await _ensure_user_from_callback(callback, session)
    if user is None or callback.message is None:
        await callback.answer()
        return

    profile = await employer_service.get_employer_profile(session, user)
    if profile is None:
        await state.set_state(EmployerOnboarding.company_name)
        await callback.message.answer(
            "Сначала укажите компанию.\n\n" + COMPANY_NAME_PROMPT,
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()
        return

    await _begin_job_creation(callback.message, state, session)
    await callback.answer()


@router.message(Command("cancel"), StateFilter(EmployerOnboarding, JobRequestCreation))
@router.message(F.text == "❌ Отмена", StateFilter(EmployerOnboarding, JobRequestCreation))
async def cancel_job_request(message: Message, state: FSMContext) -> None:
    await _clear_job_fsm(message, state)
    await message.answer("Создание заявки отменено.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "job:cancel", StateFilter(EmployerOnboarding, JobRequestCreation))
async def cancel_job_request_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _clear_job_fsm(callback, state)
    if callback.message:
        await callback.message.edit_text("Создание заявки отменено.")
        await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("jobcat:"), StateFilter(JobRequestCreation.category))
async def process_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":", 1)[1])
    categories = await worker_service.list_job_categories(session)
    category = next((item for item in categories if item.id == category_id), None)
    if category is None:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    await state.update_data(category_id=category_id, category_name=category.name_ru)
    await state.set_state(JobRequestCreation.title)
    await _update_summary_message(callback.bot, state, TITLE_PROMPT)
    await callback.answer()


@router.message(JobRequestCreation.category)
async def process_category_ignore_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await _delete_user_message(message)
    categories = await worker_service.list_job_categories(session)
    keyboard = categories_keyboard([(category.id, category.name_ru) for category in categories])
    await _update_summary_message(
        message.bot,
        state,
        f"{CATEGORY_PROMPT}\n\n<i>Выберите категорию кнопками ниже.</i>",
        keyboard,
    )


@router.message(JobRequestCreation.title)
async def process_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 1 or len(title) > 200:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Название — от 1 до 200 символов.\n\n" + TITLE_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(title=title)
    await state.set_state(JobRequestCreation.description)
    await _update_summary_message(message.bot, state, DESCRIPTION_PROMPT)


@router.message(JobRequestCreation.description)
async def process_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if len(description) < 1:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Описание не может быть пустым.\n\n" + DESCRIPTION_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(description=description)
    await state.set_state(JobRequestCreation.metro)
    await _update_summary_message(message.bot, state, METRO_LINES_PROMPT, metro_lines_keyboard())


@router.message(JobRequestCreation.metro)
async def process_metro_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_summary_message(
        message.bot,
        state,
        f"{METRO_LINES_PROMPT}\n\n<i>Выберите линию и станцию кнопками ниже.</i>",
        metro_lines_keyboard(),
    )


@router.callback_query(F.data == "jobmback:lines", StateFilter(JobRequestCreation.metro))
async def metro_back_to_lines(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_summary_message(callback.bot, state, METRO_LINES_PROMPT, metro_lines_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("jobmline:"), StateFilter(JobRequestCreation.metro))
async def metro_select_line(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    line_id = int(callback.data.split(":", 1)[1])
    line = SPB_METRO_LINE_BY_ID.get(line_id)
    if line is None:
        await callback.answer("Линия не найдена", show_alert=True)
        return

    stations = await worker_service.list_metro_stations_by_line_name(session, line.name)
    if not stations:
        await callback.answer("Станции не загружены. Обратитесь к администратору.", show_alert=True)
        return

    keyboard = metro_stations_keyboard([(station.id, station.name) for station in stations])
    tail = f"{line.emoji} <b>{line.name}</b>\nВыберите <b>станцию</b>:"
    await _update_summary_message(callback.bot, state, tail, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("jobmst:"), StateFilter(JobRequestCreation.metro))
async def metro_select_station(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    station_id = int(callback.data.split(":", 1)[1])
    station = await worker_service.get_metro_station_by_id(session, station_id)
    if station is None:
        await callback.answer("Станция не найдена", show_alert=True)
        return

    metro_name = f"{station.name} ({station.line_name})"
    await state.update_data(
        metro_station_id=station_id,
        metro_name=metro_name,
        selected_dates=[],
        shift_slots=[],
        current_date_index=0,
    )
    await state.set_state(JobRequestCreation.hourly_rate)
    await _update_summary_message(callback.bot, state, HOURLY_RATE_PROMPT)
    await callback.answer()


@router.message(JobRequestCreation.hourly_rate)
async def process_hourly_rate(message: Message, state: FSMContext) -> None:
    rate = parse_hourly_rate(message.text or "")
    if rate is None:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Введите число, например 400.\n\n" + HOURLY_RATE_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(hourly_rate=str(rate))
    await state.set_state(JobRequestCreation.workers_needed)
    await _update_summary_message(message.bot, state, WORKERS_NEEDED_PROMPT)


@router.message(JobRequestCreation.workers_needed)
async def process_workers_needed(message: Message, state: FSMContext) -> None:
    count = parse_workers_needed(message.text or "")
    if count is None:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Введите целое число от 1 до 100.\n\n" + WORKERS_NEEDED_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(workers_needed=count)
    await state.set_state(JobRequestCreation.shift_dates)
    dates = upcoming_shift_dates()
    await _update_summary_message(
        message.bot,
        state,
        SHIFT_DATES_PROMPT,
        shift_dates_keyboard(dates, set()),
    )


@router.message(JobRequestCreation.shift_dates)
async def process_shift_dates_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    data = await state.get_data()
    selected = set(data.get("selected_dates") or [])
    dates = upcoming_shift_dates()
    await _update_summary_message(
        message.bot,
        state,
        f"{SHIFT_DATES_PROMPT}\n\n<i>Выберите даты кнопками ниже.</i>",
        shift_dates_keyboard(dates, selected),
    )


@router.callback_query(F.data.startswith("jobdate:"), StateFilter(JobRequestCreation.shift_dates))
async def process_shift_date_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    payload = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("selected_dates") or [])

    if payload == "done":
        if not selected:
            await callback.answer("Выберите хотя бы одну дату", show_alert=True)
            return
        sorted_dates = sorted(selected)
        await state.update_data(
            selected_dates=sorted_dates,
            current_date_index=0,
            shift_slots=[],
        )
        first_date = date.fromisoformat(sorted_dates[0])
        await state.set_state(JobRequestCreation.shift_start_time)
        await _update_summary_message(
            callback.bot,
            state,
            f"Дата <b>{format_shift_date(first_date)}</b>\n\n"
            "Введите <b>время начала</b> смены (ЧЧ:ММ, например 10:00):",
        )
        await callback.answer()
        return

    if payload in selected:
        selected.remove(payload)
    else:
        selected.add(payload)

    await state.update_data(selected_dates=sorted(selected))
    dates = upcoming_shift_dates()
    await _update_summary_message(
        callback.bot,
        state,
        SHIFT_DATES_PROMPT,
        shift_dates_keyboard(dates, selected),
    )
    await callback.answer()


@router.message(JobRequestCreation.shift_start_time)
async def process_shift_start_time(message: Message, state: FSMContext) -> None:
    start = parse_shift_time(message.text or "")
    if start is None:
        await _delete_user_message(message)
        data = await state.get_data()
        current_date = date.fromisoformat(data["selected_dates"][data["current_date_index"]])
        await _update_summary_message(
            message.bot,
            state,
            f"Дата <b>{format_shift_date(current_date)}</b>\n\n"
            "Введите время в формате ЧЧ:ММ (например 10:00):",
        )
        return

    await _delete_user_message(message)
    await state.update_data(current_start_time=start.strftime("%H:%M"))
    await state.set_state(JobRequestCreation.shift_end_time)
    data = await state.get_data()
    current_date = date.fromisoformat(data["selected_dates"][data["current_date_index"]])
    await _update_summary_message(
        message.bot,
        state,
        f"Дата <b>{format_shift_date(current_date)}</b>, начало <b>{start.strftime('%H:%M')}</b>\n\n"
        "Введите <b>время окончания</b> смены (ЧЧ:ММ):",
    )


@router.message(JobRequestCreation.shift_end_time)
async def process_shift_end_time(message: Message, state: FSMContext) -> None:
    end = parse_shift_time(message.text or "")
    data = await state.get_data()
    current_date = date.fromisoformat(data["selected_dates"][data["current_date_index"]])
    start = parse_shift_time(data.get("current_start_time", ""))

    if end is None or start is None:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            f"Дата <b>{format_shift_date(current_date)}</b>\n\n"
            "Введите время окончания в формате ЧЧ:ММ:",
        )
        return

    if not validate_shift_times(start, end):
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            f"Дата <b>{format_shift_date(current_date)}</b>\n\n"
            "Время окончания должно быть позже начала.\n"
            "Введите <b>время окончания</b> (ЧЧ:ММ):",
        )
        return

    await _delete_user_message(message)
    slots = list(data.get("shift_slots") or [])
    slots.append(
        {
            "shift_date": current_date.isoformat(),
            "start_time": start.strftime("%H:%M"),
            "end_time": end.strftime("%H:%M"),
        }
    )
    next_index = data["current_date_index"] + 1
    selected_dates = data["selected_dates"]

    if next_index < len(selected_dates):
        await state.update_data(shift_slots=slots, current_date_index=next_index)
        await state.set_state(JobRequestCreation.shift_start_time)
        next_date = date.fromisoformat(selected_dates[next_index])
        await _update_summary_message(
            message.bot,
            state,
            f"Дата <b>{format_shift_date(next_date)}</b>\n\n"
            "Введите <b>время начала</b> смены (ЧЧ:ММ):",
        )
        return

    await state.update_data(shift_slots=slots)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )


@router.message(JobRequestCreation.optional_menu)
async def process_optional_menu_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):\n\n<i>Выберите кнопками ниже.</i>",
        optional_fields_keyboard(),
    )


@router.callback_query(F.data.startswith("jobopt:"), StateFilter(JobRequestCreation.optional_menu))
async def process_optional_menu(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":", 1)[1]

    if action == "skip" or action == "done":
        await state.set_state(JobRequestCreation.post_to_groups)
        await _update_summary_message(callback.bot, state, POST_TO_GROUPS_PROMPT, post_to_groups_keyboard())
        await callback.answer()
        return

    prompts = {
        "address": ("Введите <b>адрес</b> объекта:", JobRequestCreation.optional_address),
        "experience": ("Минимальный <b>опыт</b> в месяцах (0–600):", JobRequestCreation.optional_experience),
        "gender": ("Выберите требуемый <b>пол</b>:", JobRequestCreation.optional_gender),
        "age": ("Минимальный <b>возраст</b> (16–70):", JobRequestCreation.optional_min_age),
        "dress": ("Введите <b>дресс-код</b>:", JobRequestCreation.optional_dress_code),
        "contact": ("Введите <b>контакт</b> для связи:", JobRequestCreation.optional_contact),
    }

    if action not in prompts:
        await callback.answer("Неверный выбор", show_alert=True)
        return

    prompt, next_state = prompts[action]
    await state.set_state(next_state)
    if action == "gender":
        await _update_summary_message(callback.bot, state, prompt, required_gender_keyboard())
    else:
        await _update_summary_message(callback.bot, state, prompt)
    await callback.answer()


@router.message(JobRequestCreation.optional_address)
async def process_optional_address(message: Message, state: FSMContext) -> None:
    address = (message.text or "").strip()
    if len(address) < 1 or len(address) > 300:
        await _delete_user_message(message)
        await _update_summary_message(message.bot, state, "Адрес — от 1 до 300 символов.\n\nВведите <b>адрес</b>:")
        return
    await _delete_user_message(message)
    await state.update_data(address=address)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )


@router.message(JobRequestCreation.optional_experience)
async def process_optional_experience(message: Message, state: FSMContext) -> None:
    months = parse_optional_int(message.text or "", min_value=0, max_value=600)
    if months is None:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Введите целое число от 0 до 600.\n\nМинимальный <b>опыт</b> в месяцах:",
        )
        return
    await _delete_user_message(message)
    await state.update_data(min_experience_months=months)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )


@router.callback_query(F.data.startswith("jobgender:"), StateFilter(JobRequestCreation.optional_gender))
async def process_optional_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = GENDER_CALLBACK_MAP.get(callback.data or "")
    if gender is None:
        await callback.answer("Неверный выбор", show_alert=True)
        return
    await state.update_data(required_gender=gender)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        callback.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "jobopt:back", StateFilter(JobRequestCreation.optional_gender))
async def optional_gender_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        callback.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )
    await callback.answer()


@router.message(JobRequestCreation.optional_gender)
async def process_optional_gender_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_summary_message(
        message.bot,
        state,
        "Выберите требуемый <b>пол</b> кнопками ниже:",
        required_gender_keyboard(),
    )


@router.message(JobRequestCreation.optional_min_age)
async def process_optional_min_age(message: Message, state: FSMContext) -> None:
    min_age = parse_optional_int(message.text or "", min_value=16, max_value=70)
    if min_age is None:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Введите число от 16 до 70.\n\nМинимальный <b>возраст</b>:",
        )
        return
    await _delete_user_message(message)
    await state.update_data(min_age=min_age)
    await state.set_state(JobRequestCreation.optional_max_age)
    await _update_summary_message(message.bot, state, "Максимальный <b>возраст</b> (16–70):")


@router.message(JobRequestCreation.optional_max_age)
async def process_optional_max_age(message: Message, state: FSMContext) -> None:
    max_age = parse_optional_int(message.text or "", min_value=16, max_value=70)
    data = await state.get_data()
    min_age = data.get("min_age")
    if max_age is None:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Введите число от 16 до 70.\n\nМаксимальный <b>возраст</b>:",
        )
        return
    if min_age is not None and min_age > max_age:
        await _delete_user_message(message)
        await _update_summary_message(
            message.bot,
            state,
            "Максимальный возраст не может быть меньше минимального.\n\n"
            "Максимальный <b>возраст</b> (16–70):",
        )
        return
    await _delete_user_message(message)
    await state.update_data(max_age=max_age)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )


@router.message(JobRequestCreation.optional_dress_code)
async def process_optional_dress_code(message: Message, state: FSMContext) -> None:
    dress = (message.text or "").strip()
    if len(dress) < 1 or len(dress) > 200:
        await _delete_user_message(message)
        await _update_summary_message(message.bot, state, "Дресс-код — от 1 до 200 символов.\n\nВведите <b>дресс-код</b>:")
        return
    await _delete_user_message(message)
    await state.update_data(dress_code=dress)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )


@router.message(JobRequestCreation.optional_contact)
async def process_optional_contact(message: Message, state: FSMContext) -> None:
    contact = (message.text or "").strip()
    if len(contact) < 1:
        await _delete_user_message(message)
        await _update_summary_message(message.bot, state, "Контакт не может быть пустым.\n\nВведите <b>контакт</b>:")
        return
    await _delete_user_message(message)
    await state.update_data(contact_info=contact)
    await state.set_state(JobRequestCreation.optional_menu)
    await _update_summary_message(
        message.bot,
        state,
        "Дополнительные поля (необязательно):",
        optional_fields_keyboard(),
    )


@router.message(JobRequestCreation.post_to_groups)
async def process_post_to_groups_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_summary_message(
        message.bot,
        state,
        f"{POST_TO_GROUPS_PROMPT}\n\n<i>Ответьте кнопками ниже.</i>",
        post_to_groups_keyboard(),
    )


@router.callback_query(F.data.startswith("jobgroups:"), StateFilter(JobRequestCreation.post_to_groups))
async def process_post_to_groups(callback: CallbackQuery, state: FSMContext) -> None:
    answer = callback.data.split(":", 1)[1]
    if answer not in {"yes", "no"}:
        await callback.answer("Неверный выбор", show_alert=True)
        return
    await state.update_data(post_to_groups=answer == "yes")
    await state.set_state(JobRequestCreation.confirm)
    await _update_summary_message(
        callback.bot,
        state,
        "<b>Проверьте заявку и сохраните:</b>",
        confirm_keyboard(),
    )
    await callback.answer()


@router.message(JobRequestCreation.confirm)
async def process_confirm_ignore_text(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() == "❌ Отмена":
        await cancel_job_request(message, state)
        return
    await _delete_user_message(message)
    await _update_summary_message(
        message.bot,
        state,
        "<b>Проверьте заявку и сохраните:</b>\n\n<i>Нажмите кнопки ниже.</i>",
        confirm_keyboard(),
    )


def _build_job_create_payload(data: dict) -> JobRequestCreate:
    shift_slots = [
        ShiftSlotCreate(
            shift_date=date.fromisoformat(slot["shift_date"]),
            start_time=time.fromisoformat(slot["start_time"]),
            end_time=time.fromisoformat(slot["end_time"]),
        )
        for slot in data.get("shift_slots") or []
    ]
    return JobRequestCreate(
        category_id=data["category_id"],
        title=data["title"],
        description=data["description"],
        metro_station_id=data["metro_station_id"],
        address=data.get("address"),
        hourly_rate=Decimal(data["hourly_rate"]),
        workers_needed=data["workers_needed"],
        min_experience_months=data.get("min_experience_months"),
        required_gender=data.get("required_gender"),
        min_age=data.get("min_age"),
        max_age=data.get("max_age"),
        dress_code=data.get("dress_code"),
        contact_info=data.get("contact_info"),
        post_to_groups=data.get("post_to_groups", False),
        notify_matching_workers=True,
        shift_slots=shift_slots,
    )


@router.callback_query(F.data.startswith("jobconfirm:"), StateFilter(JobRequestCreation.confirm))
async def process_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    action = callback.data.split(":", 1)[1]
    if action not in {"draft", "publish"}:
        await callback.answer("Неверный выбор", show_alert=True)
        return

    user = await _ensure_user_from_callback(callback, session)
    if user is None:
        await callback.answer()
        return

    employer = await employer_service.get_employer_by_user_id(session, user.id)
    if employer is None:
        await callback.answer("Профиль работодателя не найден", show_alert=True)
        return

    data = await state.get_data()
    payload = _build_job_create_payload(data)
    job = await job_service.create_job_request(session, employer.id, payload)

    if action == "publish":
        job = await job_service.update_job_request(
            session,
            employer.id,
            job.id,
            JobRequestUpdate(status=JobRequestStatus.active),
        )

    await state.clear()
    status_label = "опубликована" if job.status == JobRequestStatus.active else "сохранена как черновик"

    if callback.message:
        await callback.message.edit_text(
            f"✅ Заявка «{job.title}» {status_label}!\n\n"
            f"Статус: {job_request_status_label(job.status)}\n"
            f"Смен: {len(job.shift_slots)}"
        )
        await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
