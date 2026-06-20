from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import main_menu_keyboard

router = Router(name="start")

WELCOME_TEXT = (
    "Добро пожаловать в OutstaffingBot!\n\n"
    "Выберите роль в меню ниже или откройте Mini App."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(F.text == "👷 Работник")
async def select_worker(message: Message) -> None:
    await message.answer(
        "Режим работника. Регистрация профиля — в Phase 1.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "🏢 Работодатель")
async def select_employer(message: Message) -> None:
    await message.answer(
        "Режим работодателя. Создание заявок — в Phase 2.",
        reply_markup=main_menu_keyboard(),
    )
