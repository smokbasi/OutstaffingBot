from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.services import admin_service, audit_service, user_service

router = Router(name="admin")


def _is_admin(telegram_id: int, settings: Settings) -> bool:
    return telegram_id in settings.admin_telegram_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return
    await message.answer(
        "<b>Админ-панель</b>\n\n"
        "/admin_stats — статистика\n"
        "/admin_pending — ожидают верификации\n"
        "/admin_verify &lt;id&gt; — подтвердить работодателя\n"
        "/admin_reject &lt;id&gt; — отклонить работодателя\n"
        "/admin_audit — последние записи аудита"
    )


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    stats = await admin_service.get_admin_stats(session)
    await message.answer(
        "<b>📊 Статистика</b>\n\n"
        f"👷 Работники: {stats.workers_count}\n"
        f"🏢 Работодатели: {stats.employers_count}\n"
        f"📋 Заявки: {stats.jobs_count}\n"
        f"⏳ Ожидают верификации: {stats.pending_verifications}"
    )


@router.message(Command("admin_pending"))
async def cmd_admin_pending(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    pending = await admin_service.list_pending_employers(session)
    if not pending:
        await message.answer("Нет работодателей, ожидающих верификации.")
        return

    lines = ["<b>⏳ Ожидают верификации:</b>\n"]
    for item in pending[:20]:
        username = f"@{item.username}" if item.username else f"tg:{item.telegram_id}"
        lines.append(f"• <code>{item.id}</code> — {item.company_name} ({username})")
    await message.answer("\n".join(lines))


@router.message(Command("admin_verify"))
async def cmd_admin_verify(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /admin_verify &lt;employer_id&gt;")
        return

    from uuid import UUID

    try:
        employer_id = UUID(parts[1].strip())
    except ValueError:
        await message.answer("Неверный UUID работодателя.")
        return

    admin_user = await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
    )
    employer = await admin_service.verify_employer(
        session, employer_id, actor_id=admin_user.id, approve=True
    )
    if employer is None:
        await message.answer("Работодатель не найден.")
        return
    await session.commit()
    await message.answer(f"✅ Работодатель <b>{employer.company_name}</b> верифицирован.")


@router.message(Command("admin_reject"))
async def cmd_admin_reject(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /admin_reject &lt;employer_id&gt;")
        return

    from uuid import UUID

    try:
        employer_id = UUID(parts[1].strip())
    except ValueError:
        await message.answer("Неверный UUID работодателя.")
        return

    admin_user = await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
    )
    employer = await admin_service.verify_employer(
        session, employer_id, actor_id=admin_user.id, approve=False
    )
    if employer is None:
        await message.answer("Работодатель не найден.")
        return
    await session.commit()
    await message.answer(f"❌ Работодатель <b>{employer.company_name}</b> отклонён.")


@router.message(Command("admin_audit"))
async def cmd_admin_audit(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    entries = await audit_service.list_recent_audit_logs(session, limit=15)
    if not entries:
        await message.answer("Журнал аудита пуст.")
        return

    lines = ["<b>📜 Последние записи аудита:</b>\n"]
    for entry in entries:
        lines.append(audit_service.format_audit_entry(entry))
    await message.answer("\n".join(lines))
