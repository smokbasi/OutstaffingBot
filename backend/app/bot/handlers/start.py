from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.menu_setup import refresh_user_mini_app_menu
from app.services import employer_service, user_service, worker_service

router = Router(name="start")

WELCOME_TEXT = (
    "Добро пожаловать в OutstaffingBot!\n\n"
    "Выберите роль ниже. Mini App — синяя кнопка слева от поля ввода."
)

BANNED_TEXT = "🚫 Аккаунт заблокирован. Обратитесь в поддержку."


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, session: AsyncSession) -> None:
    if message.from_user is not None:
        user = await user_service.get_user_by_telegram_id(session, message.from_user.id)
        if user is not None:
            worker = await worker_service.get_worker_by_user_id(session, user.id)
            if worker is not None and worker.is_banned:
                await message.answer(BANNED_TEXT)
                return
            employer = await employer_service.get_employer_by_user_id(session, user.id)
            if employer is not None and employer.is_banned:
                await message.answer(BANNED_TEXT)
                return

    await refresh_user_mini_app_menu(bot, message.chat.id)
    # Сброс устаревшей ReplyKeyboard с WebApp (staging URL кэшируется клиентом).
    await message.answer("Обновляю меню…", reply_markup=ReplyKeyboardRemove())
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())
