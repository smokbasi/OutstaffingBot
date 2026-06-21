from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.menu_setup import refresh_user_mini_app_menu

router = Router(name="start")

WELCOME_TEXT = (
    "Добро пожаловать в OutstaffingBot!\n\n"
    "Выберите роль ниже. Mini App — синяя кнопка слева от поля ввода."
)


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    await refresh_user_mini_app_menu(bot, message.chat.id)
    # Сброс устаревшей ReplyKeyboard с WebApp (staging URL кэшируется клиентом).
    await message.answer("Обновляю меню…", reply_markup=ReplyKeyboardRemove())
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(F.text == "🏢 Работодатель")
async def select_employer(message: Message) -> None:
    await message.answer(
        "Режим работодателя. Создание заявок — в Phase 2.",
        reply_markup=main_menu_keyboard(),
    )
