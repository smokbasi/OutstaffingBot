from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.mini_app_urls import vacancy_apply_callback_data
from app.db.models import JobRequest, Notification, NotificationType, User, Worker
from app.services import matching_service


def format_new_vacancy_message(job: JobRequest) -> str:
    category = job.category.name_ru if job.category else "—"
    metro = job.metro_station.name if job.metro_station else "—"
    next_slot = matching_service._next_shift(job)
    shift_line = "Смена: уточняйте в карточке"
    if next_slot is not None:
        shift_line = (
            f"Смена: {next_slot.shift_date.strftime('%d.%m.%Y')} "
            f"{next_slot.start_time.strftime('%H:%M')}–{next_slot.end_time.strftime('%H:%M')}"
        )
    return (
        "🔔 <b>Новая вакансия!</b>\n\n"
        f"<b>{job.title}</b>\n"
        f"{category} · {metro}\n"
        f"{job.hourly_rate} ₽/час\n"
        f"{shift_line}"
    )


def _vacancy_keyboard(job: JobRequest, settings: Settings) -> InlineKeyboardMarkup:
    # callback_data: надёжнее web_app в личке (domain/URL) и повторного ?start= в том же чате.
    _ = settings
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Откликнуться 👷",
                    callback_data=vacancy_apply_callback_data(job.id),
                )
            ]
        ]
    )


async def _get_job_with_relations(session: AsyncSession, job_id: UUID) -> JobRequest | None:
    return await session.scalar(
        select(JobRequest)
        .options(
            selectinload(JobRequest.shift_slots),
            selectinload(JobRequest.category),
            selectinload(JobRequest.metro_station),
        )
        .where(JobRequest.id == job_id)
    )


async def notify_matching_workers(session: AsyncSession, bot: Bot, settings: Settings, job_id: UUID) -> int:
    job = await _get_job_with_relations(session, job_id)
    if job is None:
        return 0

    workers = await matching_service.find_workers_for_job(session, job)
    if not workers:
        return 0

    text = format_new_vacancy_message(job)
    keyboard = _vacancy_keyboard(job, settings)
    sent_count = 0

    for worker in workers:
        user = worker.user
        if user is None:
            continue
        try:
            await bot.send_message(user.telegram_id, text, reply_markup=keyboard)
            session.add(
                Notification(
                    user_id=user.id,
                    type=NotificationType.new_vacancy,
                    payload={"job_id": str(job.id)},
                    sent_at=datetime.now(timezone.utc),
                )
            )
            sent_count += 1
        except TelegramForbiddenError:
            user.is_blocked = True

    await session.commit()
    return sent_count


def format_new_worker_message(worker: Worker, job: JobRequest) -> str:
    category = job.category.name_ru if job.category else "—"
    name = f"{worker.first_name} {worker.last_name[0]}." if worker.last_name else worker.first_name
    return (
        "👷 <b>Новый подходящий работник!</b>\n\n"
        f"Кандидат: <b>{name}</b>, {worker.age} лет\n"
        f"Подходит к заявке: <b>{job.title}</b>\n"
        f"{category} · {job.hourly_rate} ₽/час"
    )


async def _get_worker_with_relations(session: AsyncSession, worker_id: UUID) -> Worker | None:
    return await session.scalar(
        select(Worker)
        .options(
            selectinload(Worker.experiences),
            selectinload(Worker.user),
            selectinload(Worker.metro_station),
        )
        .where(Worker.id == worker_id)
    )


async def notify_employers_for_worker(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    worker_id: UUID,
) -> int:
    worker = await _get_worker_with_relations(session, worker_id)
    if worker is None:
        return 0

    jobs = await matching_service.find_active_jobs_for_worker(session, worker)
    if not jobs:
        return 0

    sent_count = 0
    for job in jobs:
        employer = job.employer
        if employer is None or employer.user is None:
            continue
        user = employer.user
        text = format_new_worker_message(worker, job)
        try:
            await bot.send_message(user.telegram_id, text)
            session.add(
                Notification(
                    user_id=user.id,
                    type=NotificationType.new_matching_worker,
                    payload={"worker_id": str(worker.id), "job_id": str(job.id)},
                    sent_at=datetime.now(timezone.utc),
                )
            )
            sent_count += 1
        except TelegramForbiddenError:
            user.is_blocked = True

    await session.commit()
    return sent_count


async def mark_user_blocked(session: AsyncSession, user_id: UUID) -> None:
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is not None:
        user.is_blocked = True
        await session.commit()
