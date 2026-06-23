"""Tests for Mini App admin API (/admin/*)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.models import ModerationViolationLog, ModerationViolationSource, User, UserRole
from app.db.session import get_db_session
from app.main import app
from app.services import admin_stats_service, moderation_violation_service, user_block_service
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
ADMIN_TELEGRAM_ID = 9001


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid4(),
        telegram_id=ADMIN_TELEGRAM_ID,
        username="admin",
        role=UserRole.admin,
    )


@pytest.fixture
async def admin_client(admin_user: User, monkeypatch: pytest.MonkeyPatch):
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", str(ADMIN_TELEGRAM_ID))
    config.get_settings.cache_clear()

    session = MagicMock()
    session.commit = AsyncMock()

    async def override_user():
        return admin_user

    async def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client, session

    app.dependency_overrides.clear()
    config.get_settings.cache_clear()


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, ADMIN_TELEGRAM_ID, username='admin')}"
    }


@pytest.mark.asyncio
async def test_admin_stats_includes_moderation_counters(
    admin_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _session = admin_client
    stats = admin_stats_service.PlatformStats(
        users_total=10,
        workers_total=7,
        employers_total=3,
        users_blocked=2,
        employers_unverified=1,
        jobs_total=5,
        jobs_active=2,
        jobs_draft=3,
        applications_total=12,
        violations_total=4,
        moderation_flagged_users=1,
    )
    monkeypatch.setattr(
        "app.api.routes.admin.admin_stats_service.get_platform_stats",
        AsyncMock(return_value=stats),
    )

    response = await client.get("/api/v1/admin/stats", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["users_blocked"] == 2
    assert body["moderation_flagged_users"] == 1
    assert body["violations_total"] == 4


@pytest.mark.asyncio
async def test_admin_moderation_queue(admin_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _session = admin_client
    flagged_user = User(
        id=uuid4(),
        telegram_id=555001,
        username="offender",
        role=UserRole.worker,
        moderation_flagged_at=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
    )
    summary = moderation_violation_service.FlaggedUserSummary(
        user=flagged_user,
        violation_count=3,
    )
    monkeypatch.setattr(
        "app.api.routes.admin.moderation_violation_service.list_moderation_queue",
        AsyncMock(return_value=[summary]),
    )

    response = await client.get("/api/v1/admin/moderation/queue", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["telegram_id"] == 555001
    assert body[0]["violation_count"] == 3


@pytest.mark.asyncio
async def test_admin_block_user(admin_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = admin_client
    target = User(
        id=uuid4(),
        telegram_id=555002,
        username="bad",
        role=UserRole.worker,
        moderation_flagged_at=datetime(2026, 6, 10, tzinfo=UTC),
    )
    block_mock = AsyncMock(
        return_value=user_block_service.BlockActionResult(
            user=target,
            changed=True,
            message="Пользователь заблокирован.",
        )
    )
    monkeypatch.setattr("app.api.routes.admin.user_block_service.block_user", block_mock)

    response = await client.post(
        "/api/v1/admin/moderation/users/555002/block",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["changed"] is True
    block_mock.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_dismiss_moderation_user(admin_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = admin_client
    dismiss_mock = AsyncMock(
        return_value=moderation_violation_service.ModerationReviewResult(
            user=User(
                id=uuid4(),
                telegram_id=555003,
                role=UserRole.worker,
            ),
            changed=True,
            message="Заявка на блокировку отклонена, пользователь снят с review.",
        )
    )
    monkeypatch.setattr(
        "app.api.routes.admin.moderation_violation_service.dismiss_moderation_review",
        dismiss_mock,
    )

    response = await client.post(
        "/api/v1/admin/moderation/users/555003/dismiss",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dismissed"
    assert body["changed"] is True
    dismiss_mock.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_moderation_user_detail_not_found(
    admin_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _session = admin_client
    monkeypatch.setattr(
        "app.api.routes.admin.moderation_violation_service.get_violations_by_telegram_id",
        AsyncMock(return_value=(None, [])),
    )

    response = await client.get(
        "/api/v1/admin/moderation/users/999999",
        headers=_auth_headers(),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_moderation_user_detail_success(
    admin_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _session = admin_client
    user = User(
        id=uuid4(),
        telegram_id=555004,
        username="detail",
        role=UserRole.employer,
        moderation_flagged_at=datetime(2026, 6, 11, tzinfo=UTC),
    )
    violation = ModerationViolationLog(
        id=uuid4(),
        user_id=user.id,
        telegram_id=user.telegram_id,
        field="description",
        category="profanity",
        matched_term="govno",
        raw_snippet="bad govno",
        normalized_snippet="bad govno",
        source=ModerationViolationSource.mini_app,
        created_at=datetime(2026, 6, 11, 10, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "app.api.routes.admin.moderation_violation_service.get_violations_by_telegram_id",
        AsyncMock(return_value=(user, [violation])),
    )
    monkeypatch.setattr(
        "app.api.routes.admin.moderation_violation_service.count_user_violations",
        AsyncMock(return_value=1),
    )

    response = await client.get(
        "/api/v1/admin/moderation/users/555004",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["telegram_id"] == 555004
    assert body["violation_count"] == 1
    assert body["violations"][0]["matched_term"] == "govno"


@pytest.mark.asyncio
async def test_admin_forbidden_for_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "99999")
    config.get_settings.cache_clear()

    regular_user = User(
        id=uuid4(),
        telegram_id=12345,
        username="user",
        role=UserRole.worker,
    )

    async def override_user():
        return regular_user

    async def override_session():
        class DummySession:
            async def commit(self) -> None:
                return None

        yield DummySession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/admin/stats",
            headers={
                "Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 12345)}",
            },
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()
    config.get_settings.cache_clear()
