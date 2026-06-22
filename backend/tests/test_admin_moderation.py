"""Tests for user block/unblock and admin moderation (Phase 9.7)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.bot.handlers.admin_moderation import (
    _format_user_line,
    _parse_telegram_id,
    cmd_block_user,
    cmd_moderation_queue,
    cmd_violation_log,
)
from app.db.models import (
    AuditLog,
    ModerationViolationLog,
    ModerationViolationSource,
    User,
    UserRole,
)
from app.services import moderation_violation_service, user_block_service


def _sample_user(*, is_blocked: bool = False, flagged: bool = False) -> User:
    return User(
        id=uuid4(),
        telegram_id=123456789,
        username="offender",
        role=UserRole.worker,
        is_blocked=is_blocked,
        moderation_flagged_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC) if flagged else None,
    )


def test_parse_telegram_id_valid() -> None:
    assert _parse_telegram_id("/block_user 987654321") == 987654321


def test_parse_telegram_id_missing() -> None:
    assert _parse_telegram_id("/block_user") is None
    assert _parse_telegram_id("/block_user abc") is None


def test_format_user_line() -> None:
    user = _sample_user(flagged=True)
    line = _format_user_line(
        moderation_violation_service.FlaggedUserSummary(user=user, violation_count=3)
    )
    assert "123456789" in line
    assert "3 наруш." in line
    assert "активен" in line


@pytest.mark.asyncio
async def test_block_user_sets_flag_and_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    session = MagicMock()
    session.flush = AsyncMock()
    audit_mock = AsyncMock(return_value=AuditLog(id=uuid4(), action="moderation.user_block"))
    monkeypatch.setattr(
        "app.services.user_block_service.user_service.get_user_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr("app.services.user_block_service.audit_log_service.record_audit", audit_mock)

    result = await user_block_service.block_user(session, user.telegram_id, actor_telegram_id=1)

    assert result.changed is True
    assert user.is_blocked is True
    audit_mock.assert_awaited_once()
    assert audit_mock.await_args.kwargs["action"] == "moderation.user_block"


@pytest.mark.asyncio
async def test_block_user_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user(is_blocked=True)
    session = MagicMock()
    audit_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.user_block_service.user_service.get_user_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr("app.services.user_block_service.audit_log_service.record_audit", audit_mock)

    result = await user_block_service.block_user(session, user.telegram_id, actor_telegram_id=1)

    assert result.changed is False
    audit_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_unblock_user_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user(is_blocked=False)
    session = MagicMock()
    audit_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.user_block_service.user_service.get_user_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr("app.services.user_block_service.audit_log_service.record_audit", audit_mock)

    result = await user_block_service.unblock_user(session, user.telegram_id, actor_telegram_id=1)

    assert result.changed is False
    audit_mock.assert_not_awaited()


def test_ensure_not_blocked_raises() -> None:
    user = _sample_user(is_blocked=True)
    with pytest.raises(user_block_service.UserBlockedError):
        user_block_service.ensure_not_blocked(user)


def _make_message(text: str, *, user_id: int = 999) -> MagicMock:
    message = MagicMock()
    message.text = text
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_cmd_block_user_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    session = AsyncMock()
    session.commit = AsyncMock()
    block_mock = AsyncMock(
        return_value=user_block_service.BlockActionResult(
            user=user,
            changed=True,
            message="Пользователь заблокирован.",
        )
    )
    monkeypatch.setattr("app.bot.handlers.admin_moderation.user_block_service.block_user", block_mock)

    message = _make_message(f"/block_user {user.telegram_id}")
    await cmd_block_user(message, session)

    block_mock.assert_awaited_once()
    session.commit.assert_awaited_once()
    reply = message.answer.await_args.args[0]
    assert "✅" in reply


@pytest.mark.asyncio
async def test_cmd_moderation_queue_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.admin_moderation.moderation_violation_service.list_moderation_queue",
        AsyncMock(return_value=[]),
    )
    message = _make_message("/moderation_queue")
    await cmd_moderation_queue(message, session)
    assert "пуста" in message.answer.await_args.args[0].lower()


@pytest.mark.asyncio
async def test_cmd_violation_log_shows_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user(flagged=True)
    violation = ModerationViolationLog(
        id=uuid4(),
        user_id=user.id,
        telegram_id=user.telegram_id,
        field="description",
        category="profanity",
        matched_term="govno",
        raw_snippet="bad govno text",
        normalized_snippet="bad govno text",
        source=ModerationViolationSource.bot,
        created_at=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
    )
    session = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.admin_moderation.moderation_violation_service.get_violations_by_telegram_id",
        AsyncMock(return_value=(user, [violation])),
    )
    message = _make_message(f"/violation_log {user.telegram_id}")
    await cmd_violation_log(message, session)
    reply = message.answer.await_args.args[0]
    assert "govno" in reply
    assert "bad govno text" in reply


@pytest.mark.asyncio
async def test_apply_to_shift_blocked_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.db.models import Worker
    from app.services import application_service

    worker = Worker(id=uuid4(), user_id=uuid4(), first_name="A", last_name="B", age=25)
    worker.user = _sample_user(is_blocked=True)
    session = AsyncMock()
    ensure_mock = AsyncMock(side_effect=user_block_service.UserBlockedError())
    monkeypatch.setattr(
        "app.services.application_service.user_block_service.ensure_worker_not_blocked",
        ensure_mock,
    )

    with pytest.raises(user_block_service.UserBlockedError):
        await application_service.apply_to_shift(session, worker, uuid4())
