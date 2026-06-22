from datetime import date, time
from decimal import Decimal
from uuid import uuid4

from app.db.models import JobCategory, JobRequest, JobRequestStatus, MetroStation, ShiftSlot, TelegramGroup
from app.services.group_posting_service import (
    format_group_post_message,
    group_matches_job,
    group_post_keyboard,
)
from app.core.config import Settings


def _make_job(*, category_id: int = 2) -> JobRequest:
    job = JobRequest(
        id=uuid4(),
        employer_id=uuid4(),
        category_id=category_id,
        title="Официант на банкет",
        description="Обслуживание гостей",
        metro_station_id=1,
        hourly_rate=Decimal("350"),
        workers_needed=3,
        status=JobRequestStatus.active,
        post_to_groups=True,
    )
    job.category = JobCategory(id=category_id, slug="waiter", name_ru="Официант")
    job.metro_station = MetroStation(id=1, name="Сокольники", line_name="Красная")
    job.shift_slots = [
        ShiftSlot(
            id=uuid4(),
            job_request_id=job.id,
            shift_date=date(2026, 6, 20),
            start_time=time(10, 0),
            end_time=time(22, 0),
            slots_total=3,
            slots_filled=0,
        ),
        ShiftSlot(
            id=uuid4(),
            job_request_id=job.id,
            shift_date=date(2026, 6, 21),
            start_time=time(10, 0),
            end_time=time(22, 0),
            slots_total=3,
            slots_filled=0,
        ),
    ]
    return job


def test_format_group_post_message_contains_vacancy_details() -> None:
    job = _make_job()
    text = format_group_post_message(job)

    assert "Новая вакансия: Официант" in text
    assert "350 ₽/час" in text
    assert "3 чел." in text
    assert "м. Сокольники" in text
    assert "20.06 10:00–22:00" in text
    assert "21.06 10:00–22:00" in text
    assert "Официант на банкет" in text
    assert "Обслуживание гостей" in text


def test_format_group_post_message_closed_marker() -> None:
    job = _make_job()
    text = format_group_post_message(job, closed=True)
    assert "❌" in text
    assert "Закрыто" in text


def test_group_matches_job_all_categories_when_empty_filter() -> None:
    job = _make_job(category_id=2)
    group = TelegramGroup(id=1, chat_id=-100, title="Test", category_ids=None, is_active=True)
    assert group_matches_job(group, job) is True

    group_empty = TelegramGroup(id=2, chat_id=-101, title="Test2", category_ids=[], is_active=True)
    assert group_matches_job(group_empty, job) is True


def test_group_matches_job_respects_category_filter() -> None:
    job = _make_job(category_id=2)
    matching = TelegramGroup(id=1, chat_id=-100, title="Waiters", category_ids=[2, 5], is_active=True)
    other = TelegramGroup(id=2, chat_id=-101, title="Bar", category_ids=[5], is_active=True)
    inactive = TelegramGroup(id=3, chat_id=-102, title="Old", category_ids=[2], is_active=False)

    assert group_matches_job(matching, job) is True
    assert group_matches_job(other, job) is False
    assert group_matches_job(inactive, job) is False


def test_group_post_keyboard_uses_vacancy_deep_link() -> None:
    job = _make_job()
    settings = Settings(mini_app_url="https://www.outstaffingbot.online/?v=2")
    keyboard = group_post_keyboard(job, settings)
    assert keyboard is not None
    button = keyboard.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == f"https://www.outstaffingbot.online/vacancy/{job.id}?v=2"
