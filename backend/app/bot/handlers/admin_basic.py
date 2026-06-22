"""Admin stats, employer verification, audit log (Phase 9.8)."""

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import IsAdminFilter
from app.db.models import AuditLog
from app.services import admin_stats_service, audit_log_service, employer_service

router = Router(name="admin_basic")
router.message.filter(IsAdminFilter())


def _parse_telegram_id(text: str) -> int | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    try:
        return int(parts[1].strip())
    except ValueError:
        return None


def _format_stats(stats: admin_stats_service.PlatformStats) -> str:
    return (
        "<b>Статистика платформы</b>\n\n"
        f"👥 Пользователи: {stats.users_total} "
        f"(работники {stats.workers_total}, работодатели {stats.employers_total})\n"
        f"🚫 Заблокированы: {stats.users_blocked}\n"
        f"⚠️ В очереди модерации: {stats.moderation_flagged_users}\n"
        f"🏢 Неверифицированные работодатели: {stats.employers_unverified}\n\n"
        f"📋 Заявки: {stats.jobs_total} "
        f"(активные {stats.jobs_active}, черновики {stats.jobs_draft})\n"
        f"📝 Отклики: {stats.applications_total}\n"
        f"🛡 Нарушения модерации: {stats.violations_total}"
    )


def _format_audit_entry(entry: AuditLog) -> str:
    created = entry.created_at.strftime("%d.%m.%Y %H:%M")
    actor = f"<code>{entry.actor_telegram_id}</code>" if entry.actor_telegram_id else "—"
    target = f"<code>{entry.target_telegram_id}</code>" if entry.target_telegram_id else "—"
    details = f" | {entry.details}" if entry.details else ""
    return f"{created} | {entry.action} | actor {actor} → {target}{details}"


@router.message(Command("admin_stats"), F.chat.type == ChatType.PRIVATE)
async def cmd_admin_stats(message: Message, session: AsyncSession) -> None:
    stats = await admin_stats_service.get_platform_stats(session)
    text = _format_stats(stats)
    text += "\n\n<code>/unverified_employers</code> — список для верификации"
    await message.answer(text)


@router.message(Command("unverified_employers"), F.chat.type == ChatType.PRIVATE)
async def cmd_unverified_employers(message: Message, session: AsyncSession) -> None:
    rows = await admin_stats_service.list_unverified_employers(session)
    if not rows:
        await message.answer("Все работодатели верифицированы.")
        return

    lines = ["<b>Неверифицированные работодатели:</b>"]
    for employer, user in rows[:30]:
        username = f"@{user.username}" if user.username else "—"
        created = employer.created_at.strftime("%d.%m.%Y")
        lines.append(
            f"• <code>{user.telegram_id}</code> {username} — {employer.company_name} ({created})"
        )
    if len(rows) > 30:
        lines.append(f"\n… и ещё {len(rows) - 30}")
    lines.append("\nВерификация: <code>/verify_employer &lt;telegram_id&gt;</code>")
    await message.answer("\n".join(lines))


@router.message(Command("verify_employer"), F.chat.type == ChatType.PRIVATE)
async def cmd_verify_employer(message: Message, session: AsyncSession) -> None:
    telegram_id = _parse_telegram_id(message.text or "")
    if telegram_id is None:
        await message.answer("Использование: <code>/verify_employer &lt;telegram_id&gt;</code>")
        return
    if message.from_user is None:
        return

    result = await employer_service.verify_employer_by_telegram_id(
        session,
        telegram_id,
        actor_telegram_id=message.from_user.id,
    )
    await session.commit()
    prefix = "✅" if result.changed else "ℹ️"
    await message.answer(f"{prefix} {result.message}")


@router.message(Command("audit_log"), F.chat.type == ChatType.PRIVATE)
async def cmd_audit_log(message: Message, session: AsyncSession) -> None:
    telegram_id = _parse_telegram_id(message.text or "")
    entries = await audit_log_service.list_recent_audit(
        session,
        target_telegram_id=telegram_id,
        limit=25,
    )
    if not entries:
        hint = f" для <code>{telegram_id}</code>" if telegram_id is not None else ""
        await message.answer(f"Записей audit_log{hint} нет.")
        return

    header = (
        f"<b>Audit log</b> — пользователь <code>{telegram_id}</code>\n"
        if telegram_id is not None
        else "<b>Последние записи audit_log:</b>\n"
    )
    lines = [header]
    for entry in entries:
        lines.append(_format_audit_entry(entry))
    await message.answer("\n".join(lines))
