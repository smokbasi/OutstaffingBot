"""Tests for moderation violation persistence (Phase 9.6)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.db.models import ModerationViolationSource, User, UserRole
from app.services import content_moderation_service, moderation_violation_service


def _sample_violation() -> content_moderation_service.ModerationViolation:
    return content_moderation_service.ModerationViolation(
        field="description",
        matched_term="govno",
        normalized_snippet="govno",
        raw_snippet="Это govno текст",
        category="profanity",
    )


def _sample_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=987654321,
        username="employer",
        role=UserRole.employer,
    )


@pytest.mark.asyncio
async def test_record_content_rejection_persists_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODERATION_VIOLATION_THRESHOLD", "5")
    get_settings.cache_clear()

    user = _sample_user()
    session = MagicMock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=1)

    flagged = await moderation_violation_service.record_content_rejection(
        session,
        user,
        content_moderation_service.ContentRejectedError(_sample_violation()),
        source=ModerationViolationSource.mini_app,
    )

    assert flagged is False
    assert user.moderation_flagged_at is None
    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.user_id == user.id
    assert added.telegram_id == user.telegram_id
    assert added.field == "description"
    assert added.matched_term == "govno"
    assert added.raw_snippet == "Это govno текст"
    assert added.source == ModerationViolationSource.mini_app
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_record_content_rejection_flags_user_at_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODERATION_VIOLATION_THRESHOLD", "3")
    get_settings.cache_clear()

    user = _sample_user()
    session = MagicMock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=3)

    flagged = await moderation_violation_service.record_content_rejection(
        session,
        user,
        content_moderation_service.ContentRejectedError(_sample_violation()),
        source=ModerationViolationSource.bot,
    )

    assert flagged is True
    assert user.moderation_flagged_at is not None
    assert user.moderation_flagged_at.tzinfo is not None


@pytest.mark.asyncio
async def test_record_content_rejection_does_not_reflag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODERATION_VIOLATION_THRESHOLD", "1")
    get_settings.cache_clear()

    user = _sample_user()
    user.moderation_flagged_at = datetime(2026, 1, 1, tzinfo=UTC)
    session = MagicMock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=2)

    flagged = await moderation_violation_service.record_content_rejection(
        session,
        user,
        content_moderation_service.ContentRejectedError(_sample_violation()),
        source=ModerationViolationSource.api,
    )

    assert flagged is False
    assert user.moderation_flagged_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_violation_includes_raw_snippet_and_category() -> None:
    violation = content_moderation_service.check_text("description", "Это полный govno текст")
    assert violation is not None
    assert violation.raw_snippet
    assert "govno" in violation.raw_snippet.lower()
    assert violation.category in {"profanity", "translit", None}


def test_content_rejected_error_does_not_expose_matched_term() -> None:
    exc = content_moderation_service.ContentRejectedError(_sample_violation())
    assert str(exc) == content_moderation_service.CONTENT_REJECTED_MESSAGE
    assert "govno" not in str(exc)
