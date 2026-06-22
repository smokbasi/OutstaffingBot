"""Tests for admin stats, employer verification, audit log (Phase 9.8)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.bot.handlers.admin_basic import (
    _format_audit_entry,
    _format_stats,
    cmd_admin_stats,
    cmd_audit_log,
    cmd_verify_employer,
)
from app.db.models import AuditLog, Employer, User, UserRole
from app.services import admin_stats_service, employer_service
from app.services.employer_service import EmployerNotVerifiedError


def _sample_user(*, telegram_id: int = 123456789) -> User:
    return User(
        id=uuid4(),
        telegram_id=telegram_id,
        username="employer1",
        role=UserRole.employer,
    )


def _sample_employer(user: User, *, verified: bool = False) -> Employer:
    return Employer(
        id=uuid4(),
        user_id=user.id,
        company_name="ООО Тест",
        verified=verified,
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


def test_format_stats() -> None:
    stats = admin_stats_service.PlatformStats(
        users_total=10,
        workers_total=7,
        employers_total=3,
        users_blocked=1,
        employers_unverified=2,
        jobs_total=5,
        jobs_active=2,
        jobs_draft=3,
        applications_total=12,
        violations_total=4,
        moderation_flagged_users=1,
    )
    text = _format_stats(stats)
    assert "10" in text
    assert "Неверифицированные" in text
    assert "4" in text


def test_format_audit_entry() -> None:
    entry = AuditLog(
        id=uuid4(),
        action="employer.verify",
        actor_telegram_id=1,
        target_telegram_id=123456789,
        details={"company_name": "ООО Тест"},
        created_at=datetime(2026, 6, 3, 15, 30, tzinfo=UTC),
    )
    text = _format_audit_entry(entry)
    assert "employer.verify" in text
    assert "123456789" in text
    assert "ООО Тест" in text


def test_ensure_verified_raises() -> None:
    user = _sample_user()
    employer = _sample_employer(user, verified=False)
    with pytest.raises(EmployerNotVerifiedError):
        employer_service.ensure_verified(employer)


@pytest.mark.asyncio
async def test_verify_employer_sets_flag_and_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    employer = _sample_employer(user, verified=False)
    session = MagicMock()
    session.flush = AsyncMock()
    audit_mock = AsyncMock(return_value=AuditLog(id=uuid4(), action="employer.verify"))
    monkeypatch.setattr(
        "app.services.employer_service.user_service.get_user_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.services.employer_service.get_employer_by_user_id",
        AsyncMock(return_value=employer),
    )
    monkeypatch.setattr("app.services.employer_service.audit_log_service.record_audit", audit_mock)

    result = await employer_service.verify_employer_by_telegram_id(
        session,
        user.telegram_id,
        actor_telegram_id=999,
    )

    assert result.changed is True
    assert employer.verified is True
    audit_mock.assert_awaited_once()
    assert audit_mock.await_args.kwargs["action"] == "employer.verify"


@pytest.mark.asyncio
async def test_verify_employer_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    employer = _sample_employer(user, verified=True)
    session = MagicMock()
    audit_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.employer_service.user_service.get_user_by_telegram_id",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(
        "app.services.employer_service.get_employer_by_user_id",
        AsyncMock(return_value=employer),
    )
    monkeypatch.setattr("app.services.employer_service.audit_log_service.record_audit", audit_mock)

    result = await employer_service.verify_employer_by_telegram_id(
        session,
        user.telegram_id,
        actor_telegram_id=999,
    )

    assert result.changed is False
    audit_mock.assert_not_awaited()


def _make_message(text: str, *, user_id: int = 999) -> MagicMock:
    message = MagicMock()
    message.text = text
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_cmd_admin_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    stats = admin_stats_service.PlatformStats(
        users_total=1,
        workers_total=1,
        employers_total=0,
        users_blocked=0,
        employers_unverified=0,
        jobs_total=0,
        jobs_active=0,
        jobs_draft=0,
        applications_total=0,
        violations_total=0,
        moderation_flagged_users=0,
    )
    session = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.admin_basic.admin_stats_service.get_platform_stats",
        AsyncMock(return_value=stats),
    )
    message = _make_message("/admin_stats")
    await cmd_admin_stats(message, session)
    assert "Статистика" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_cmd_verify_employer_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    employer = _sample_employer(user)
    session = AsyncMock()
    session.commit = AsyncMock()
    verify_mock = AsyncMock(
        return_value=employer_service.VerifyActionResult(
            employer=employer,
            user=user,
            changed=True,
            message="Работодатель верифицирован.",
        )
    )
    monkeypatch.setattr(
        "app.bot.handlers.admin_basic.employer_service.verify_employer_by_telegram_id",
        verify_mock,
    )
    message = _make_message(f"/verify_employer {user.telegram_id}")
    await cmd_verify_employer(message, session)
    verify_mock.assert_awaited_once()
    session.commit.assert_awaited_once()
    assert "✅" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_cmd_audit_log_shows_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = AuditLog(
        id=uuid4(),
        action="moderation.user_block",
        actor_telegram_id=1,
        target_telegram_id=123456789,
        details=None,
        created_at=datetime(2026, 6, 3, tzinfo=UTC),
    )
    session = AsyncMock()
    monkeypatch.setattr(
        "app.bot.handlers.admin_basic.audit_log_service.list_recent_audit",
        AsyncMock(return_value=[entry]),
    )
    message = _make_message("/audit_log")
    await cmd_audit_log(message, session)
    assert "moderation.user_block" in message.answer.await_args.args[0]
