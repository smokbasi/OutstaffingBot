from aiogram import Bot, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.worker_registration import _begin_registration
from app.bot.helpers.vacancy_present import send_job_vacancy_for_apply
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.menu_setup import refresh_user_mini_app_menu
from app.core.mini_app_urls import parse_job_start_payload
from app.services import user_service, worker_service

router = Router(name="start")

WELCOME_TEXT = (
    "Добро пожаловать в OutstaffingBot!\n\n"
    "Выберите роль ниже. Mini App — синяя кнопка слева от поля ввода."
)


@router.message(CommandStart(deep_link="job_"))
async def cmd_start_job(
    message: Message,
    bot: Bot,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    job_id = parse_job_start_payload(command.args)
    if job_id is None:
        await message.answer(
            "Ссылка на вакансию некорректна.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await refresh_user_mini_app_menu(bot, message.chat.id)
    await message.answer("Обновляю меню…", reply_markup=ReplyKeyboardRemove())

    user = await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
    )
    worker = await worker_service.get_worker_by_user_id(session, user.id)

    if worker is None or not worker.resume_completed:
        await message.answer(
            "Чтобы откликнуться на вакансию, сначала заполните профиль работника."
        )
        await _begin_registration(message, state, pending_job_id=str(job_id))
        return

    sent = await send_job_vacancy_for_apply(message, session, worker, state, job_id)
    if not sent:
        await message.answer(
            "Вакансия недоступна или уже закрыта.",
            reply_markup=main_menu_keyboard(),
        )


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    await refresh_user_mini_app_menu(bot, message.chat.id)
    # Сброс устаревшей ReplyKeyboard с WebApp (staging URL кэшируется клиентом).
    await message.answer("Обновляю меню…", reply_markup=ReplyKeyboardRemove())
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())
