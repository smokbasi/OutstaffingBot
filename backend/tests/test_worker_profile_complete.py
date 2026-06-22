from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers.start import cmd_start_job
from app.bot.handlers.worker_registration import start_registration
from app.db.models import Gender, User, UserRole, Worker, WorkerExperience
from app.schemas.worker import WorkerExperienceRead, WorkerProfileRead
from app.services import worker_service


def _make_worker(*, resume_completed: bool = False, with_experience: bool = True) -> Worker:
    worker = Worker(
        id=uuid4(),
        user_id=uuid4(),
        first_name="Никита",
        last_name="Милашевич",
        age=24,
        gender=Gender.male,
        metro_station_id=1,
        min_hourly_rate=Decimal("400"),
        resume_completed=resume_completed,
    )
    if with_experience:
        worker.experiences = [
            WorkerExperience(
                id=uuid4(),
                worker_id=worker.id,
                category_id=1,
                role_title="Официант",
                duration_months=12,
            )
        ]
    else:
        worker.experiences = []
    return worker


def test_is_profile_complete_when_resume_flag_set() -> None:
    worker = _make_worker(resume_completed=True)
    assert worker_service.is_profile_complete(worker) is True


def test_is_profile_complete_when_all_fields_filled_without_flag() -> None:
    worker = _make_worker(resume_completed=False)
    assert worker_service.is_profile_complete(worker) is True


def test_is_profile_complete_false_when_missing_experience() -> None:
    worker = _make_worker(resume_completed=False, with_experience=False)
    assert worker_service.is_profile_complete(worker) is False


def test_is_profile_complete_false_when_worker_none() -> None:
    assert worker_service.is_profile_complete(None) is False


def test_is_profile_read_complete_matches_worker_rules() -> None:
    profile = WorkerProfileRead(
        id=uuid4(),
        first_name="Никита",
        last_name="Милашевич",
        age=24,
        gender=Gender.male,
        metro_station_id=1,
        metro_station_name="Автово",
        min_hourly_rate=Decimal("400"),
        resume_completed=False,
        experiences=[
            WorkerExperienceRead(
                id=uuid4(),
                category_id=1,
                category_name="Официант",
                role_title="Официант зала",
                duration_months=12,
                description=None,
            )
        ],
    )
    assert worker_service.is_profile_read_complete(profile) is True


def _make_message(text: str = "📝 Заполнить профиль") -> MagicMock:
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 12345
    message.from_user.username = "nikita"
    message.from_user.language_code = "ru"
    message.text = text
    message.answer = AsyncMock()
    return message


async def _make_state() -> FSMContext:
    storage = MemoryStorage()
    return FSMContext(storage=storage, key=MagicMock())


@pytest.mark.asyncio
async def test_start_registration_prompts_when_profile_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _make_message()
    session = AsyncMock()
    state = await _make_state()
    user = User(id=uuid4(), telegram_id=12345, username="nikita", role=UserRole.worker)
    profile = WorkerProfileRead(
        id=uuid4(),
        first_name="Никита",
        last_name="Милашевич",
        age=24,
        gender=Gender.male,
        metro_station_id=1,
        metro_station_name="Автово",
        min_hourly_rate=Decimal("400"),
        resume_completed=True,
        experiences=[
            WorkerExperienceRead(
                id=uuid4(),
                category_id=1,
                category_name="Официант",
                role_title="Официант зала",
                duration_months=12,
                description=None,
            )
        ],
    )
    monkeypatch.setattr(
        "app.bot.handlers.worker_registration._ensure_user",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.bot.handlers.worker_registration.worker_service.get_worker_profile",
        AsyncMock(return_value=profile),
    )
    begin_mock = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.worker_registration._begin_registration",
        begin_mock,
    )

    await start_registration(message, session, state)

    begin_mock.assert_not_awaited()
    message.answer.assert_awaited_once()
    reply = message.answer.await_args.args[0]
    assert "Профиль уже заполнен" in reply
    assert "Никита" in reply


@pytest.mark.asyncio
async def test_start_registration_starts_fsm_when_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _make_message()
    session = AsyncMock()
    state = await _make_state()
    user = User(id=uuid4(), telegram_id=12345, username="nikita", role=UserRole.worker)
    monkeypatch.setattr(
        "app.bot.handlers.worker_registration._ensure_user",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.bot.handlers.worker_registration.worker_service.get_worker_profile",
        AsyncMock(return_value=None),
    )
    begin_mock = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.worker_registration._begin_registration",
        begin_mock,
    )

    await start_registration(message, session, state)

    begin_mock.assert_awaited_once_with(message, state)


@pytest.mark.asyncio
async def test_cmd_start_job_skips_fsm_for_complete_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid4()
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 12345
    message.from_user.username = "nikita"
    message.from_user.language_code = "ru"
    message.chat = MagicMock()
    message.chat.id = 12345
    message.answer = AsyncMock()
    bot = MagicMock()
    bot.send_message = AsyncMock()
    command = MagicMock()
    command.args = f"job_{job_id}"
    session = AsyncMock()
    state = await _make_state()
    user = User(id=uuid4(), telegram_id=12345, username="nikita", role=UserRole.worker)
    worker = _make_worker(resume_completed=True)

    monkeypatch.setattr(
        "app.bot.handlers.start.refresh_user_mini_app_menu",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.bot.handlers.start.user_service.get_or_create_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.bot.handlers.start.worker_service.get_worker_by_user_id",
        AsyncMock(return_value=worker),
    )
    begin_mock = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.start._begin_registration",
        begin_mock,
    )
    vacancy_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.bot.handlers.start.send_job_vacancy_for_apply",
        vacancy_mock,
    )

    await cmd_start_job(message, bot, command, session, state)

    begin_mock.assert_not_awaited()
    vacancy_mock.assert_awaited_once()
    assert vacancy_mock.await_args.args[4] == job_id


@pytest.mark.asyncio
async def test_cmd_start_job_starts_fsm_when_profile_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid4()
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 12345
    message.from_user.username = "nikita"
    message.from_user.language_code = "ru"
    message.chat = MagicMock()
    message.chat.id = 12345
    message.answer = AsyncMock()
    bot = MagicMock()
    command = MagicMock()
    command.args = f"job_{job_id}"
    session = AsyncMock()
    state = await _make_state()
    user = User(id=uuid4(), telegram_id=12345, username="nikita", role=UserRole.worker)

    monkeypatch.setattr(
        "app.bot.handlers.start.refresh_user_mini_app_menu",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.bot.handlers.start.user_service.get_or_create_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.bot.handlers.start.worker_service.get_worker_by_user_id",
        AsyncMock(return_value=None),
    )
    begin_mock = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.start._begin_registration",
        begin_mock,
    )
    vacancy_mock = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.start.send_job_vacancy_for_apply",
        vacancy_mock,
    )

    await cmd_start_job(message, bot, command, session, state)

    begin_mock.assert_awaited_once()
    assert begin_mock.await_args.kwargs["pending_job_id"] == str(job_id)
    vacancy_mock.assert_not_awaited()
