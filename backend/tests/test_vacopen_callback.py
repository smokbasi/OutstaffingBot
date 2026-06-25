from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers.vacancy_search import open_vacancy_from_button
from app.db.models import User, UserRole, Worker


async def _make_state() -> FSMContext:
    storage = MemoryStorage()
    return FSMContext(storage=storage, key=MagicMock())


@pytest.mark.asyncio
async def test_open_vacancy_from_push_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid4()
    callback = MagicMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 12345
    callback.data = f"vacopen:{job_id}"
    callback.message = MagicMock()
    callback.message.chat.type = "private"
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()

    bot = MagicMock()
    session = AsyncMock()
    state = await _make_state()

    user = User(id=uuid4(), telegram_id=12345, username="worker", role=UserRole.worker)
    worker = Worker(
        id=uuid4(),
        user_id=user.id,
        first_name="Иван",
        last_name="Иванов",
        age=25,
        resume_completed=True,
    )

    monkeypatch.setattr(
        "app.bot.handlers.vacancy_search._ensure_user_from_callback",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.bot.handlers.vacancy_search.worker_service.get_worker_by_user_id",
        AsyncMock(return_value=worker),
    )
    monkeypatch.setattr(
        "app.bot.handlers.vacancy_search.worker_service.is_profile_complete",
        lambda w: True,
    )
    vacancy_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.bot.handlers.vacancy_search.send_job_vacancy_for_apply",
        vacancy_mock,
    )

    await open_vacancy_from_button(callback, bot, session, state)

    callback.answer.assert_awaited_once()
    vacancy_mock.assert_awaited_once()
    assert vacancy_mock.await_args.args[4] == job_id
