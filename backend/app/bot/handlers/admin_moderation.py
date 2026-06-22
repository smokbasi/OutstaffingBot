from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import IsAdminFilter
from app.services import moderation_violation_service, user_block_service

router = Router(name="admin_moderation")
router.message.filter(IsAdminFilter())


def _parse_telegram_id(text: str) -> int | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    try:
        return int(parts[1].strip())
    except ValueError:
        return None


def _format_user_line(summary: moderation_violation_service.FlaggedUserSummary) -> str:
    user = summary.user
    username = f"@{user.username}" if user.username else "—"
    blocked = "заблокирован" if user.is_blocked else "активен"
    flagged_at = (
        user.moderation_flagged_at.strftime("%d.%m.%Y %H:%M")
        if user.moderation_flagged_at
        else "—"
    )
    return (
        f"• <code>{user.telegram_id}</code> {username} — "
        f"{summary.violation_count} наруш., {blocked}, review {flagged_at}"
    )


@router.message(
    Command("moderation_queue", "admin_violations"),
    F.chat.type == ChatType.PRIVATE,
)
async def cmd_moderation_queue(message: Message, session: AsyncSession) -> None:
    queue = await moderation_violation_service.list_moderation_queue(session)
    if not queue:
        await message.answer(
            "Очередь модерации пуста.\n"
            f"Пользователи попадают сюда после {get_settings_threshold()} нарушений."
        )
        return

    lines = ["<b>Очередь модерации:</b>"]
    for item in queue[:30]:
        lines.append(_format_user_line(item))
    if len(queue) > 30:
        lines.append(f"\n… и ещё {len(queue) - 30}")
    lines.append("\nДетали: <code>/violation_log &lt;telegram_id&gt;</code>")
    await message.answer("\n".join(lines))


def get_settings_threshold() -> int:
    from app.core.config import get_settings

    return get_settings().moderation_violation_threshold


@router.message(Command("violation_log"), F.chat.type == ChatType.PRIVATE)
async def cmd_violation_log(message: Message, session: AsyncSession) -> None:
    telegram_id = _parse_telegram_id(message.text or "")
    if telegram_id is None:
        await message.answer("Использование: <code>/violation_log &lt;telegram_id&gt;</code>")
        return

    user, violations = await moderation_violation_service.get_violations_by_telegram_id(
        session,
        telegram_id,
    )
    if user is None:
        await message.answer(f"Пользователь <code>{telegram_id}</code> не найден.")
        return

    if not violations:
        await message.answer(
            f"<b>Telegram ID:</b> <code>{telegram_id}</code>\n"
            f"Статус: {'заблокирован' if user.is_blocked else 'активен'}\n\n"
            "Нарушений модерации нет."
        )
        return

    username = f"@{user.username}" if user.username else "—"
    lines = [
        f"<b>Лог нарушений</b> — <code>{telegram_id}</code> {username}",
        f"Всего: {len(violations)}, статус: {'заблокирован' if user.is_blocked else 'активен'}",
        "",
    ]
    for index, item in enumerate(violations[:20], start=1):
        created = item.created_at.strftime("%d.%m.%Y %H:%M")
        category = item.category or "—"
        lines.append(
            f"{index}. {created} | {item.source.value} | поле <code>{item.field}</code>\n"
            f"   term: <code>{item.matched_term}</code> ({category})\n"
            f"   snippet: {item.raw_snippet[:200]}"
        )
    if len(violations) > 20:
        lines.append(f"\n… показаны последние 20 из {len(violations)}")
    lines.append(
        "\nБлок: <code>/block_user "
        f"{telegram_id}</code> | разблок: <code>/unblock_user {telegram_id}</code>"
    )
    await message.answer("\n".join(lines))


@router.message(Command("block_user"), F.chat.type == ChatType.PRIVATE)
async def cmd_block_user(message: Message, session: AsyncSession) -> None:
    telegram_id = _parse_telegram_id(message.text or "")
    if telegram_id is None:
        await message.answer("Использование: <code>/block_user &lt;telegram_id&gt;</code>")
        return
    if message.from_user is None:
        return

    result = await user_block_service.block_user(
        session,
        telegram_id,
        actor_telegram_id=message.from_user.id,
    )
    await session.commit()
    prefix = "✅" if result.changed else "ℹ️"
    await message.answer(f"{prefix} {result.message}")


@router.message(Command("unblock_user"), F.chat.type == ChatType.PRIVATE)
async def cmd_unblock_user(message: Message, session: AsyncSession) -> None:
    telegram_id = _parse_telegram_id(message.text or "")
    if telegram_id is None:
        await message.answer("Использование: <code>/unblock_user &lt;telegram_id&gt;</code>")
        return
    if message.from_user is None:
        return

    result = await user_block_service.unblock_user(
        session,
        telegram_id,
        actor_telegram_id=message.from_user.id,
    )
    await session.commit()
    prefix = "✅" if result.changed else "ℹ️"
    await message.answer(f"{prefix} {result.message}")
