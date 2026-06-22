from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import (
    Application,
    ApplicationStatus,
    GroupPost,
    JobCategory,
    JobRequest,
    JobRequestStatus,
    MetroStation,
    ShiftSlot,
    TelegramGroup,
)
from app.services.group_posting_service import (
    count_accepted_applications,
    is_job_headcount_filled,
    reopen_group_posts,
    sync_group_posts_for_headcount,
)


def _make_job(*, workers_needed: int = 2) -> JobRequest:
    job = JobRequest(
        id=uuid4(),
        employer_id=uuid4(),
        category_id=2,
        title="Официант",
        description="Смена",
        metro_station_id=1,
        hourly_rate=Decimal("350"),
        workers_needed=workers_needed,
        status=JobRequestStatus.active,
        post_to_groups=True,
    )
    job.category = JobCategory(id=2, slug="waiter", name_ru="Официант")
    job.metro_station = MetroStation(id=1, name="Сокольники", line_name="Красная")
    job.shift_slots = [
        ShiftSlot(
            id=uuid4(),
            job_request_id=job.id,
            shift_date=date(2026, 6, 20),
            start_time=time(10, 0),
            end_time=time(22, 0),
            slots_total=workers_needed,
            slots_filled=0,
        )
    ]
    return job


@pytest.mark.asyncio
async def test_count_accepted_applications() -> None:
    job_id = uuid4()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=2)

    count = await count_accepted_applications(session, job_id)

    assert count == 2
    session.scalar.assert_awaited_once()


def test_is_job_headcount_filled() -> None:
    job = _make_job(workers_needed=3)
    assert is_job_headcount_filled(job, 2) is False
    assert is_job_headcount_filled(job, 3) is True
    assert is_job_headcount_filled(job, 4) is True


@pytest.mark.asyncio
async def test_sync_group_posts_closes_when_headcount_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_job(workers_needed=2)
    bot = AsyncMock()
    settings = MagicMock()
    posts = [GroupPost(id=1, job_request_id=job.id, group_id=1, message_id=10)]

    session = AsyncMock()
    edit_mock = AsyncMock(return_value=1)

    monkeypatch.setattr(
        "app.services.group_posting_service._get_job_with_relations",
        AsyncMock(return_value=job),
    )
    monkeypatch.setattr(
        "app.services.group_posting_service.count_accepted_applications",
        AsyncMock(return_value=2),
    )
    monkeypatch.setattr(
        "app.services.group_posting_service._get_group_posts",
        AsyncMock(return_value=posts),
    )
    monkeypatch.setattr("app.services.group_posting_service._edit_group_posts", edit_mock)

    result = await sync_group_posts_for_headcount(session, bot, settings, job.id)

    assert result == 1
    edit_mock.assert_awaited_once()
    assert edit_mock.await_args.kwargs["closed"] is True


@pytest.mark.asyncio
async def test_sync_group_posts_reopens_when_headcount_not_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_job(workers_needed=3)
    bot = AsyncMock()
    settings = MagicMock()
    posts = [GroupPost(id=1, job_request_id=job.id, group_id=1, message_id=10)]

    session = AsyncMock()
    edit_mock = AsyncMock(return_value=1)

    monkeypatch.setattr(
        "app.services.group_posting_service._get_job_with_relations",
        AsyncMock(return_value=job),
    )
    monkeypatch.setattr(
        "app.services.group_posting_service.count_accepted_applications",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        "app.services.group_posting_service._get_group_posts",
        AsyncMock(return_value=posts),
    )
    monkeypatch.setattr("app.services.group_posting_service._edit_group_posts", edit_mock)

    result = await sync_group_posts_for_headcount(session, bot, settings, job.id)

    assert result == 1
    edit_mock.assert_awaited_once()
    assert edit_mock.await_args.kwargs["closed"] is False


@pytest.mark.asyncio
async def test_sync_group_posts_skips_inactive_job(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_job()
    job.status = JobRequestStatus.cancelled
    bot = AsyncMock()
    settings = MagicMock()
    session = AsyncMock()

    monkeypatch.setattr(
        "app.services.group_posting_service._get_job_with_relations",
        AsyncMock(return_value=job),
    )
    close_mock = AsyncMock()
    reopen_mock = AsyncMock()
    monkeypatch.setattr("app.services.group_posting_service.close_group_posts", close_mock)
    monkeypatch.setattr("app.services.group_posting_service.reopen_group_posts", reopen_mock)

    result = await sync_group_posts_for_headcount(session, bot, settings, job.id)

    assert result == 0
    close_mock.assert_not_awaited()
    reopen_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reopen_group_posts_edits_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_job()
    group = TelegramGroup(id=1, chat_id=-100, title="Test", category_ids=None, is_active=True)
    post = GroupPost(
        id=1,
        job_request_id=job.id,
        group_id=group.id,
        message_id=42,
        group=group,
    )
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=MagicMock(username="TestBot"))
    settings = MagicMock()
    settings.mini_app_url = "https://example.com"
    settings.bot_username = "Outstaffing_Work_BOT"
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=lambda: [post]))
    session.commit = AsyncMock()

    monkeypatch.setattr(
        "app.services.group_posting_service._get_job_with_relations",
        AsyncMock(return_value=job),
    )
    monkeypatch.setattr(
        "app.services.group_posting_service._get_group_posts",
        AsyncMock(return_value=[post]),
    )

    updated = await reopen_group_posts(session, bot, settings, job.id)

    assert updated == 1
    bot.edit_message_text.assert_awaited_once()
    call_kwargs = bot.edit_message_text.await_args.kwargs
    assert "Закрыто" not in call_kwargs["text"]
    assert call_kwargs["reply_markup"] is not None
    session.commit.assert_awaited_once()
