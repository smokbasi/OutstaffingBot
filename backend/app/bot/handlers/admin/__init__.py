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
        "/admin_verify_worker &lt;id&gt; — подтвердить работника\n"
        "/admin_reject_worker &lt;id&gt; — отклонить работника\n"
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

    pending_employers = await admin_service.list_pending_employers(session)
    pending_workers = await admin_service.list_pending_workers(session)
    if not pending_employers and not pending_workers:
        await message.answer("Нет профилей, ожидающих верификации.")
        return

    lines = ["<b>⏳ Ожидают верификации:</b>\n"]
    if pending_employers:
        lines.append("<b>Компании:</b>")
        for item in pending_employers[:10]:
            username = f"@{item.username}" if item.username else f"tg:{item.telegram_id}"
            lines.append(f"• <code>{item.id}</code> — {item.company_name} ({username})")
    if pending_workers:
        lines.append("\n<b>Работники:</b>")
        for item in pending_workers[:10]:
            username = f"@{item.username}" if item.username else f"tg:{item.telegram_id}"
            name = f"{item.first_name} {item.last_name}"
            lines.append(f"• <code>{item.id}</code> — {name} ({username})")
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


@router.message(Command("admin_verify_worker"))
async def cmd_admin_verify_worker(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /admin_verify_worker &lt;worker_id&gt;")
        return

    from uuid import UUID

    try:
        worker_id = UUID(parts[1].strip())
    except ValueError:
        await message.answer("Неверный UUID работника.")
        return

    admin_user = await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
    )
    worker = await admin_service.verify_worker(
        session, worker_id, actor_id=admin_user.id, approve=True
    )
    if worker is None:
        await message.answer("Работник не найден.")
        return
    await session.commit()
    await message.answer(
        f"✅ Работник <b>{worker.first_name} {worker.last_name}</b> верифицирован."
    )


@router.message(Command("admin_reject_worker"))
async def cmd_admin_reject_worker(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /admin_reject_worker &lt;worker_id&gt;")
        return

    from uuid import UUID

    try:
        worker_id = UUID(parts[1].strip())
    except ValueError:
        await message.answer("Неверный UUID работника.")
        return

    admin_user = await user_service.get_or_create_by_telegram_id(
        session,
        message.from_user.id,
        username=message.from_user.username,
    )
    worker = await admin_service.verify_worker(
        session, worker_id, actor_id=admin_user.id, approve=False
    )
    if worker is None:
        await message.answer("Работник не найден.")
        return
    await session.commit()
    await message.answer(
        f"❌ Работник <b>{worker.first_name} {worker.last_name}</b> отклонён."
    )


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
