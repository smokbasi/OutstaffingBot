from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import IsAdminFilter
from app.services import group_posting_service

router = Router(name="admin_groups")
router.message.filter(IsAdminFilter())


def _parse_category_ids(text: str) -> list[int] | None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return None
    raw = parts[1].replace(" ", "")
    if raw.lower() in {"all", "все", "*"}:
        return None
    return [int(item) for item in raw.split(",") if item]


def _format_category_ids(category_ids: list[int] | None) -> str:
    if not category_ids:
        return "все категории"
    return ", ".join(str(item) for item in category_ids)


_PRIVATE_GROUP_COMMAND_HINT = (
    "Эта команда работает только в группе.\n\n"
    "Добавьте бота в нужную группу, сделайте его администратором "
    "с правом публиковать сообщения и выполните команду там."
)


@router.message(
    Command("register_group", "unregister_group", "group_status"),
    F.chat.type == ChatType.PRIVATE,
)
async def cmd_group_commands_private_only(message: Message) -> None:
    command = (message.text or "").split(maxsplit=1)[0].lstrip("/").split("@", 1)[0]
    if command == "register_group":
        await message.answer(
            _PRIVATE_GROUP_COMMAND_HINT
            + "\n\nВ группе: <code>/register_group</code> — все категории, "
            "<code>/register_group 2,5</code> — только выбранные."
        )
        return
    if command == "unregister_group":
        await message.answer(
            _PRIVATE_GROUP_COMMAND_HINT + "\n\nВ группе: <code>/unregister_group</code>."
        )
        return
    await message.answer(
        _PRIVATE_GROUP_COMMAND_HINT + "\n\nВ группе: <code>/group_status</code>."
    )


@router.message(Command("register_group"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_register_group(message: Message, session: AsyncSession) -> None:
    category_ids = _parse_category_ids(message.text or "")
    group = await group_posting_service.register_telegram_group(
        session,
        chat_id=message.chat.id,
        title=message.chat.title,
        category_ids=category_ids,
    )
    await message.answer(
        "✅ Группа привязана.\n"
        f"Категории: {_format_category_ids(group.category_ids)}\n\n"
        "Убедитесь, что бот — администратор с правом публиковать сообщения.\n"
        "Пример: <code>/register_group 2,5</code> — только категории 2 и 5.\n"
        "Без аргументов — все категории."
    )


@router.message(Command("unregister_group"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_unregister_group(message: Message, session: AsyncSession) -> None:
    group = await group_posting_service.deactivate_telegram_group(session, message.chat.id)
    if group is None:
        await message.answer("Эта группа не была зарегистрирована.")
        return
    await message.answer("✅ Группа отключена от автопубликации.")


@router.message(Command("group_status"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_group_status(message: Message, session: AsyncSession) -> None:
    groups = await group_posting_service.list_telegram_groups(session)
    current = next((item for item in groups if item.chat_id == message.chat.id), None)
    if current is None or not current.is_active:
        await message.answer(
            "Группа не зарегистрирована.\n"
            "Админ: /register_group — включить автопубликацию."
        )
        return
    await message.answer(
        f"Группа активна.\n"
        f"Название: {current.title or '—'}\n"
        f"Категории: {_format_category_ids(current.category_ids)}"
    )


@router.message(Command("admin_groups"), F.chat.type == ChatType.PRIVATE)
async def cmd_admin_groups(message: Message, session: AsyncSession) -> None:
    groups = await group_posting_service.list_telegram_groups(session)
    if not groups:
        await message.answer(
            "Зарегистрированных групп пока нет.\n"
            "Добавьте бота в группу и выполните там /register_group."
        )
        return

    lines = ["<b>Telegram-группы для публикаций:</b>"]
    for group in groups:
        status = "активна" if group.is_active else "отключена"
        lines.append(
            f"• {group.title or group.chat_id} — {status}, "
            f"категории: {_format_category_ids(group.category_ids)}"
        )
    await message.answer("\n".join(lines))
