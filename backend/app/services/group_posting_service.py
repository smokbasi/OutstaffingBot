import logging
from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramMigrateToChat
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.mini_app_urls import vacancy_deep_link

logger = logging.getLogger(__name__)
from app.db.models import Application, ApplicationStatus, GroupPost, JobRequest, JobRequestStatus, TelegramGroup


def _format_shift_lines(job: JobRequest) -> str:
    slots = sorted(job.shift_slots, key=lambda slot: (slot.shift_date, slot.start_time))
    if not slots:
        return "📅 Смены уточняйте в карточке"
    parts = [
        f"{slot.shift_date.strftime('%d.%m')} "
        f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}"
        for slot in slots
    ]
    return f"📅 {', '.join(parts)}"


def format_group_post_message(job: JobRequest, *, closed: bool = False) -> str:
    category = job.category.name_ru if job.category else "—"
    metro = job.metro_station.name if job.metro_station else "—"
    rate = int(job.hourly_rate) if job.hourly_rate == int(job.hourly_rate) else job.hourly_rate
    lines = [
        f"🔔 <b>Новая вакансия: {category}</b>",
        f"💰 {rate} ₽/час  |  👥 {job.workers_needed} чел.",
        f"📍 м. {metro}",
        _format_shift_lines(job),
        "",
        f"<b>{job.title}</b>",
        job.description.strip(),
    ]
    if closed:
        lines.extend(["", "❌ <b>Закрыто</b>"])
    return "\n".join(lines)


def group_post_keyboard(job: JobRequest, settings: Settings, *, closed: bool = False) -> InlineKeyboardMarkup | None:
    if closed:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Откликнуться 👷",
                    web_app=WebAppInfo(url=vacancy_deep_link(settings, job.id)),
                )
            ]
        ]
    )


def group_matches_job(group: TelegramGroup, job: JobRequest) -> bool:
    if not group.is_active:
        return False
    if not group.category_ids:
        return True
    return job.category_id in group.category_ids


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


async def count_accepted_applications(session: AsyncSession, job_id: UUID) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(Application)
        .where(
            Application.job_request_id == job_id,
            Application.status == ApplicationStatus.accepted,
        )
    )
    return int(count or 0)


def is_job_headcount_filled(job: JobRequest, accepted_count: int) -> bool:
    return accepted_count >= job.workers_needed


async def _get_group_posts(session: AsyncSession, job_id: UUID) -> list[GroupPost]:
    stmt = (
        select(GroupPost)
        .options(selectinload(GroupPost.group))
        .where(GroupPost.job_request_id == job_id, GroupPost.message_id.is_not(None))
    )
    return list(await session.scalars(stmt))


async def _edit_group_posts(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    job: JobRequest,
    posts: list[GroupPost],
    *,
    closed: bool,
) -> int:
    text = format_group_post_message(job, closed=closed)
    keyboard = group_post_keyboard(job, settings, closed=closed)
    updated_count = 0

    for post in posts:
        group = post.group
        if group is None or post.message_id is None:
            continue
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=group.chat_id,
                message_id=post.message_id,
                reply_markup=keyboard,
            )
            updated_count += 1
        except TelegramBadRequest:
            continue
        except TelegramForbiddenError:
            group.is_active = False

    await session.commit()
    return updated_count


async def find_groups_for_job(session: AsyncSession, job: JobRequest) -> list[TelegramGroup]:
    stmt = select(TelegramGroup).where(TelegramGroup.is_active.is_(True))
    groups = list(await session.scalars(stmt))
    return [group for group in groups if group_matches_job(group, job)]


async def register_telegram_group(
    session: AsyncSession,
    *,
    chat_id: int,
    title: str | None,
    category_ids: list[int] | None,
) -> TelegramGroup:
    existing = await session.scalar(select(TelegramGroup).where(TelegramGroup.chat_id == chat_id))
    if existing is not None:
        existing.title = title
        existing.category_ids = category_ids
        existing.is_active = True
        await session.flush()
        return existing

    group = TelegramGroup(
        chat_id=chat_id,
        title=title,
        category_ids=category_ids,
        is_active=True,
    )
    session.add(group)
    await session.flush()
    return group


async def migrate_telegram_group_chat_id(
    session: AsyncSession,
    *,
    old_chat_id: int,
    new_chat_id: int,
    title: str | None = None,
) -> TelegramGroup | None:
    group = await session.scalar(select(TelegramGroup).where(TelegramGroup.chat_id == old_chat_id))
    if group is None:
        return None
    group.chat_id = new_chat_id
    if title is not None:
        group.title = title
    await session.flush()
    return group


async def deactivate_telegram_group(session: AsyncSession, chat_id: int) -> TelegramGroup | None:
    group = await session.scalar(select(TelegramGroup).where(TelegramGroup.chat_id == chat_id))
    if group is None:
        return None
    group.is_active = False
    await session.flush()
    return group


async def list_telegram_groups(session: AsyncSession) -> list[TelegramGroup]:
    stmt = select(TelegramGroup).order_by(TelegramGroup.is_active.desc(), TelegramGroup.title)
    return list(await session.scalars(stmt))


async def post_job_to_groups(session: AsyncSession, bot: Bot, settings: Settings, job_id: UUID) -> int:
    job = await _get_job_with_relations(session, job_id)
    if job is None or job.status != JobRequestStatus.active or not job.post_to_groups:
        return 0

    groups = await find_groups_for_job(session, job)
    if not groups:
        return 0

    text = format_group_post_message(job)
    keyboard = group_post_keyboard(job, settings)
    posted_count = 0

    for group in groups:
        existing = await session.scalar(
            select(GroupPost).where(
                GroupPost.job_request_id == job.id,
                GroupPost.group_id == group.id,
            )
        )
        if existing is not None:
            continue

        try:
            message = await bot.send_message(group.chat_id, text, reply_markup=keyboard)
        except TelegramMigrateToChat as exc:
            migrated = await migrate_telegram_group_chat_id(
                session,
                old_chat_id=group.chat_id,
                new_chat_id=exc.migrate_to_chat_id,
                title=group.title,
            )
            if migrated is None:
                logger.warning(
                    "Group migrate for job %s: chat %s -> %s but group row missing",
                    job.id,
                    group.chat_id,
                    exc.migrate_to_chat_id,
                )
                continue
            group = migrated
            try:
                message = await bot.send_message(group.chat_id, text, reply_markup=keyboard)
            except (TelegramBadRequest, TelegramForbiddenError) as retry_exc:
                logger.warning(
                    "Failed to post job %s to migrated group %s: %s",
                    job.id,
                    group.chat_id,
                    retry_exc,
                )
                if isinstance(retry_exc, TelegramForbiddenError):
                    group.is_active = False
                continue
        except TelegramForbiddenError:
            group.is_active = False
            continue
        except TelegramBadRequest as exc:
            logger.warning(
                "Failed to post job %s to group %s (%s): %s",
                job.id,
                group.chat_id,
                group.title,
                exc,
            )
            continue
        else:
            session.add(
                GroupPost(
                    job_request_id=job.id,
                    group_id=group.id,
                    message_id=message.message_id,
                    posted_at=datetime.now(timezone.utc),
                )
            )
            posted_count += 1

    await session.commit()
    return posted_count


async def close_group_posts(session: AsyncSession, bot: Bot, settings: Settings, job_id: UUID) -> int:
    job = await _get_job_with_relations(session, job_id)
    if job is None:
        return 0

    posts = await _get_group_posts(session, job_id)
    if not posts:
        return 0

    return await _edit_group_posts(session, bot, settings, job, posts, closed=True)


async def reopen_group_posts(session: AsyncSession, bot: Bot, settings: Settings, job_id: UUID) -> int:
    job = await _get_job_with_relations(session, job_id)
    if job is None:
        return 0

    posts = await _get_group_posts(session, job_id)
    if not posts:
        return 0

    return await _edit_group_posts(session, bot, settings, job, posts, closed=False)


async def sync_group_posts_for_headcount(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    job_id: UUID,
) -> int:
    job = await _get_job_with_relations(session, job_id)
    if job is None or not job.post_to_groups or job.status != JobRequestStatus.active:
        return 0

    posts = await _get_group_posts(session, job_id)
    if not posts:
        return 0

    accepted_count = await count_accepted_applications(session, job_id)
    closed = is_job_headcount_filled(job, accepted_count)
    return await _edit_group_posts(session, bot, settings, job, posts, closed=closed)
