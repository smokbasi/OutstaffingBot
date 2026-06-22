from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.helpers.vacancy_present import send_job_vacancy_for_apply
from app.reference.spb_metro import SPB_METRO_LINE_BY_ID
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.worker_registration import (
    categories_keyboard,
    confirm_inline_keyboard,
    experience_more_keyboard,
    gender_inline_keyboard,
    metro_lines_keyboard,
    metro_stations_keyboard,
    profile_already_complete_keyboard,
)
from app.bot.states.worker_registration import WorkerRegistration
from app.db.models import Gender
from app.services import user_service, worker_service

router = Router(name="worker_registration")

GENDER_LABELS = {
    Gender.male: "Мужской",
    Gender.female: "Женский",
    Gender.other: "Другое",
    Gender.prefer_not_say: "Не указывать",
}

GENDER_CALLBACK_MAP = {
    "gender:male": Gender.male,
    "gender:female": Gender.female,
    "gender:other": Gender.other,
    "gender:prefer_not_say": Gender.prefer_not_say,
}

FIRST_NAME_PROMPT = "Введите <b>имя</b>:"
LAST_NAME_PROMPT = "Введите <b>фамилию</b>:"
AGE_PROMPT = "Введите <b>возраст</b> (16–70):"
GENDER_PROMPT = "Выберите <b>пол</b>:"
METRO_LINES_PROMPT = "Выберите <b>линию метро</b>:"


async def _ensure_user(message: Message, session: AsyncSession):
    if message.from_user is None:
        return None
    return await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
    )


def _format_resume_header(data: dict) -> str:
    lines = [
        "<b>Анкета работника</b>",
        f"Имя: {data.get('first_name', '—')}",
        f"Фамилия: {data.get('last_name', '—')}",
        f"Возраст: {data.get('age', '—')}",
        f"Пол: {GENDER_LABELS.get(data.get('gender'), '—')}",
    ]
    if data.get("metro_name"):
        lines.append(f"Метро: {data['metro_name']}")
    if data.get("min_hourly_rate"):
        lines.append(f"Мин. ставка: {data['min_hourly_rate']} ₽/час")
    experiences = data.get("experiences") or []
    if experiences:
        lines.append("")
        lines.append("<b>Опыт:</b>")
        for idx, exp in enumerate(experiences, start=1):
            lines.append(
                f"{idx}. {exp['category_name']} — {exp['role_title']} ({exp['duration_months']} мес.)"
            )
    return "\n".join(lines)


def _resume_text(data: dict, tail: str) -> str:
    return f"{_format_resume_header(data)}\n\n{tail}"


async def _start_resume_message(
    message: Message,
    state: FSMContext,
    tail: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    sent = await message.answer(_resume_text(data, tail), reply_markup=reply_markup)
    await state.update_data(resume_chat_id=sent.chat.id, resume_message_id=sent.message_id)


async def _update_resume_message(
    bot: Bot,
    state: FSMContext,
    tail: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    chat_id = data.get("resume_chat_id")
    message_id = data.get("resume_message_id")
    if chat_id is None or message_id is None:
        return
    try:
        await bot.edit_message_text(
            _resume_text(data, tail),
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


async def _begin_registration(
    message: Message,
    state: FSMContext,
    *,
    pending_job_id: str | None = None,
    prefill: dict | None = None,
) -> None:
    await state.clear()
    if pending_job_id is not None:
        await state.update_data(pending_job_id=pending_job_id)
    if prefill:
        await state.update_data(**prefill, edit_mode=True)
    await state.set_state(WorkerRegistration.first_name)
    prompt = FIRST_NAME_PROMPT
    if prefill:
        prompt = (
            "Можете изменить данные — пройдите шаги заново или сохраните как есть на последнем шаге.\n\n"
            + FIRST_NAME_PROMPT
        )
    await _start_resume_message(message, state, prompt)


@router.message(F.text == "👷 Работник")
async def select_worker(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_user(message, session)
    if user is None:
        return

    profile = await worker_service.get_worker_profile(session, user)
    if profile and worker_service.is_profile_read_complete(profile):
        await message.answer(
            f"{worker_service.format_worker_profile_text(profile)}\n\n"
            "Чтобы обновить профиль — нажмите «📝 Заполнить профиль».",
            reply_markup=main_menu_keyboard(),
        )
        return

    await _begin_registration(message, state)


@router.message(F.text == "📝 Заполнить профиль")
async def start_registration(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_user(message, session)
    if user is None:
        return

    profile = await worker_service.get_worker_profile(session, user)
    if profile and worker_service.is_profile_read_complete(profile):
        await message.answer(
            f"{worker_service.format_worker_profile_text(profile)}\n\n"
            "<b>Профиль уже заполнен.</b> Хотите обновить данные?",
            reply_markup=profile_already_complete_keyboard(),
        )
        return

    await _begin_registration(message, state)


@router.callback_query(F.data == "reg:update")
async def start_registration_update(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.get_or_create_by_telegram_id(
        session,
        callback.from_user.id,
        username=callback.from_user.username,
        language_code=callback.from_user.language_code,
    )
    profile = await worker_service.get_worker_profile(session, user)
    if profile is None or not worker_service.is_profile_read_complete(profile):
        if callback.message:
            await callback.message.edit_text("Профиль не найден. Начинаем заполнение с начала.")
            await _begin_registration(callback.message, state)
        await callback.answer()
        return

    prefill = worker_service.profile_to_registration_state(profile)
    if callback.message:
        await callback.message.edit_text("Обновление профиля…")
        await _begin_registration(callback.message, state, prefill=prefill)
    await callback.answer()


@router.callback_query(F.data == "reg:dismiss")
async def dismiss_profile_update(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text("Ок, профиль без изменений.")
        await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("cancel"), StateFilter(WorkerRegistration))
@router.message(F.text == "❌ Отмена", StateFilter(WorkerRegistration))
async def cancel_registration(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("resume_chat_id") and data.get("resume_message_id"):
        await _delete_message_safe(message.bot, data["resume_chat_id"], data["resume_message_id"])
    await state.clear()
    await message.answer("Регистрация отменена.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "reg:cancel", StateFilter(WorkerRegistration))
async def cancel_registration_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message:
        await callback.message.edit_text("Регистрация отменена.")
        await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await state.clear()
    await callback.answer()


@router.message(WorkerRegistration.first_name)
async def process_first_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 1 or len(name) > 100:
        await _delete_user_message(message)
        await _update_resume_message(
            message.bot,
            state,
            "Имя должно быть от 1 до 100 символов.\n\n" + FIRST_NAME_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(first_name=name)
    await state.set_state(WorkerRegistration.last_name)
    await _update_resume_message(message.bot, state, LAST_NAME_PROMPT)


@router.message(WorkerRegistration.last_name)
async def process_last_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 1 or len(name) > 100:
        await _delete_user_message(message)
        await _update_resume_message(
            message.bot,
            state,
            "Фамилия должна быть от 1 до 100 символов.\n\n" + LAST_NAME_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(last_name=name)
    await state.set_state(WorkerRegistration.age)
    await _update_resume_message(message.bot, state, AGE_PROMPT)


@router.message(WorkerRegistration.age)
async def process_age(message: Message, state: FSMContext) -> None:
    try:
        age = int((message.text or "").strip())
    except ValueError:
        await _delete_user_message(message)
        await _update_resume_message(message.bot, state, "Введите число от 16 до 70.\n\n" + AGE_PROMPT)
        return
    if age < 16 or age > 70:
        await _delete_user_message(message)
        await _update_resume_message(
            message.bot,
            state,
            "Возраст должен быть от 16 до 70.\n\n" + AGE_PROMPT,
        )
        return

    await _delete_user_message(message)
    await state.update_data(age=age)
    await state.set_state(WorkerRegistration.gender)
    await _update_resume_message(message.bot, state, GENDER_PROMPT, gender_inline_keyboard())


@router.message(WorkerRegistration.gender)
async def process_gender_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_resume_message(
        message.bot,
        state,
        f"{GENDER_PROMPT}\n\n<i>Выберите пол кнопками ниже.</i>",
        gender_inline_keyboard(),
    )


@router.callback_query(F.data.startswith("gender:"), StateFilter(WorkerRegistration.gender))
async def process_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = GENDER_CALLBACK_MAP.get(callback.data or "")
    if gender is None:
        await callback.answer("Неверный выбор", show_alert=True)
        return

    await state.update_data(gender=gender)
    await state.set_state(WorkerRegistration.metro)
    await _update_resume_message(callback.bot, state, METRO_LINES_PROMPT, metro_lines_keyboard())
    await callback.answer()


@router.message(WorkerRegistration.metro)
async def process_metro_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_resume_message(
        message.bot,
        state,
        f"{METRO_LINES_PROMPT}\n\n<i>Выберите линию и станцию кнопками ниже.</i>",
        metro_lines_keyboard(),
    )


@router.callback_query(F.data == "mback:lines", StateFilter(WorkerRegistration.metro))
async def metro_back_to_lines(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_resume_message(callback.bot, state, METRO_LINES_PROMPT, metro_lines_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("mline:"), StateFilter(WorkerRegistration.metro))
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
    await _update_resume_message(callback.bot, state, tail, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("mst:"), StateFilter(WorkerRegistration.metro))
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
        experiences=[],
    )
    await state.set_state(WorkerRegistration.experience_category)

    categories = await worker_service.list_job_categories(session)
    keyboard = categories_keyboard([(category.id, category.name_ru) for category in categories])
    await _update_resume_message(
        callback.bot,
        state,
        "Выберите <b>категорию опыта</b>:",
        keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"), StateFilter(WorkerRegistration.experience_category))
async def process_experience_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    category_id = int(callback.data.split(":", 1)[1])
    categories = await worker_service.list_job_categories(session)
    category = next((item for item in categories if item.id == category_id), None)
    if category is None:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await state.update_data(
        current_category_id=category_id,
        current_category_name=category.name_ru,
    )
    await state.set_state(WorkerRegistration.experience_title)
    await _update_resume_message(
        callback.bot,
        state,
        f"Категория: <b>{category.name_ru}</b>\n\nВведите <b>должность</b> (например: официант зала):",
        None,
    )
    await callback.answer()


@router.message(WorkerRegistration.experience_title)
async def process_experience_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 1 or len(title) > 200:
        await _delete_user_message(message)
        data = await state.get_data()
        await _update_resume_message(
            message.bot,
            state,
            f"Категория: <b>{data.get('current_category_name', '—')}</b>\n\n"
            "Должность должна быть от 1 до 200 символов.\n\n"
            "Введите <b>должность</b> (например: официант зала):",
        )
        return

    await _delete_user_message(message)
    await state.update_data(current_role_title=title)
    await state.set_state(WorkerRegistration.experience_months)
    await _update_resume_message(
        message.bot,
        state,
        f"Должность: <b>{title}</b>\n\nСколько <b>месяцев</b> опыта в этой роли?",
        None,
    )


@router.message(WorkerRegistration.experience_months)
async def process_experience_months(message: Message, state: FSMContext) -> None:
    try:
        months = int((message.text or "").strip())
    except ValueError:
        await _delete_user_message(message)
        data = await state.get_data()
        await _update_resume_message(
            message.bot,
            state,
            f"Должность: <b>{data.get('current_role_title', '—')}</b>\n\n"
            "Введите целое число месяцев (0–600):",
        )
        return
    if months < 0 or months > 600:
        await _delete_user_message(message)
        data = await state.get_data()
        await _update_resume_message(
            message.bot,
            state,
            f"Должность: <b>{data.get('current_role_title', '—')}</b>\n\n"
            "Стаж должен быть от 0 до 600 месяцев:",
        )
        return

    await _delete_user_message(message)
    data = await state.get_data()
    experiences = list(data.get("experiences", []))
    experiences.append(
        {
            "category_id": data["current_category_id"],
            "category_name": data["current_category_name"],
            "role_title": data["current_role_title"],
            "duration_months": months,
        }
    )
    await state.update_data(experiences=experiences)
    await state.set_state(WorkerRegistration.experience_more)
    await _update_resume_message(
        message.bot,
        state,
        f"Опыт добавлен: {data['current_category_name']} — {data['current_role_title']}.\n"
        "Добавить ещё опыт?",
        experience_more_keyboard(),
    )


@router.message(WorkerRegistration.experience_more)
async def process_experience_more_ignore_text(message: Message, state: FSMContext) -> None:
    await _delete_user_message(message)
    await _update_resume_message(
        message.bot,
        state,
        "Добавить ещё опыт?\n\n<i>Ответьте кнопками ниже.</i>",
        experience_more_keyboard(),
    )


@router.callback_query(F.data.startswith("exp_more:"), StateFilter(WorkerRegistration.experience_more))
async def process_experience_more(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    answer = (callback.data or "").split(":", 1)[1]

    if answer == "yes":
        await state.set_state(WorkerRegistration.experience_category)
        categories = await worker_service.list_job_categories(session)
        keyboard = categories_keyboard([(category.id, category.name_ru) for category in categories])
        await _update_resume_message(
            callback.bot,
            state,
            "Выберите категорию для следующего опыта:",
            keyboard,
        )
        await callback.answer()
        return

    if answer != "no":
        await callback.answer("Неверный выбор", show_alert=True)
        return

    data = await state.get_data()
    if not data.get("experiences"):
        await state.set_state(WorkerRegistration.experience_category)
        categories = await worker_service.list_job_categories(session)
        keyboard = categories_keyboard([(category.id, category.name_ru) for category in categories])
        await _update_resume_message(
            callback.bot,
            state,
            "Нужен хотя бы один опыт. Выберите <b>категорию опыта</b>:",
            keyboard,
        )
        await callback.answer()
        return

    await state.set_state(WorkerRegistration.min_rate)
    await _update_resume_message(
        callback.bot,
        state,
        "Укажите <b>минимальную почасовую ставку</b> (₽/час, только число):",
        None,
    )
    await callback.answer()


@router.message(WorkerRegistration.min_rate)
async def process_min_rate(message: Message, state: FSMContext) -> None:
    try:
        rate = Decimal((message.text or "").strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        await _delete_user_message(message)
        await _update_resume_message(
            message.bot,
            state,
            "Введите число, например 350.\n\n"
            "Укажите <b>минимальную почасовую ставку</b> (₽/час, только число):",
        )
        return
    if rate < 0:
        await _delete_user_message(message)
        await _update_resume_message(
            message.bot,
            state,
            "Ставка не может быть отрицательной.\n\n"
            "Укажите <b>минимальную почасовую ставку</b> (₽/час, только число):",
        )
        return

    await _delete_user_message(message)
    await state.update_data(min_hourly_rate=str(rate))
    await state.set_state(WorkerRegistration.confirm)
    await _update_resume_message(
        message.bot,
        state,
        "<b>Проверьте данные и сохраните профиль:</b>",
        confirm_inline_keyboard(),
    )


@router.message(WorkerRegistration.confirm)
async def process_confirm_ignore_text(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() == "❌ Отмена":
        await cancel_registration(message, state)
        return
    await _delete_user_message(message)
    await _update_resume_message(
        message.bot,
        state,
        "<b>Проверьте данные и сохраните профиль:</b>\n\n<i>Нажмите кнопки ниже.</i>",
        confirm_inline_keyboard(),
    )


@router.callback_query(F.data == "reg:save", StateFilter(WorkerRegistration.confirm))
async def process_confirm_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.get_or_create_by_telegram_id(
        session,
        callback.from_user.id,
        username=callback.from_user.username,
        language_code=callback.from_user.language_code,
    )

    data = await state.get_data()
    pending_job_id = data.get("pending_job_id")
    profile = await worker_service.save_worker_registration(
        session,
        user,
        first_name=data["first_name"],
        last_name=data["last_name"],
        age=data["age"],
        gender=data["gender"].value if data.get("gender") else None,
        metro_station_id=data["metro_station_id"],
        min_hourly_rate=Decimal(data["min_hourly_rate"]),
        experiences=data.get("experiences", []),
    )
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            f"✅ Профиль сохранён!\n\n"
            f"{profile.first_name} {profile.last_name}, {profile.age} лет\n"
            f"Откройте Mini App — профиль будет там же.",
        )
        worker = await worker_service.get_worker_by_user_id(session, user.id)
        if pending_job_id and worker is not None:
            from uuid import UUID

            sent = await send_job_vacancy_for_apply(
                callback.message,
                session,
                worker,
                state,
                UUID(pending_job_id),
            )
            if not sent:
                await callback.message.answer(
                    "Вакансия недоступна или уже закрыта.",
                    reply_markup=main_menu_keyboard(),
                )
        else:
            await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
