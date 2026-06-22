import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.enums import ChatType

from app.bot.handlers.admin_groups import (
    _format_category_ids,
    _parse_category_ids,
    cmd_group_commands_private_only,
    cmd_register_group,
    cmd_unregister_group,
)
from app.db.models import TelegramGroup


def test_parse_category_ids_all_keywords() -> None:
    assert _parse_category_ids("/register_group all") is None
    assert _parse_category_ids("/register_group все") is None


def test_parse_category_ids_specific() -> None:
    assert _parse_category_ids("/register_group 2,5,7") == [2, 5, 7]


def test_parse_category_ids_empty_args() -> None:
    assert _parse_category_ids("/register_group") is None


def test_format_category_ids() -> None:
    assert _format_category_ids(None) == "все категории"
    assert _format_category_ids([2, 5]) == "2, 5"


def _make_message(
    *,
    chat_type: ChatType,
    text: str,
    chat_id: int = -100123,
    title: str | None = "Test Group",
) -> MagicMock:
    message = MagicMock()
    message.text = text
    message.chat = MagicMock()
    message.chat.id = chat_id
    message.chat.type = chat_type
    message.chat.title = title
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_register_group_in_group_replies_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _make_message(chat_type=ChatType.SUPERGROUP, text="/register_group 2,5")
    session = AsyncMock()
    group = TelegramGroup(
        id=1,
        chat_id=message.chat.id,
        title="Test Group",
        category_ids=[2, 5],
        is_active=True,
    )
    register_mock = AsyncMock(return_value=group)
    monkeypatch.setattr(
        "app.bot.handlers.admin_groups.group_posting_service.register_telegram_group",
        register_mock,
    )

    await cmd_register_group(message, session)

    register_mock.assert_awaited_once_with(
        session,
        chat_id=message.chat.id,
        title="Test Group",
        category_ids=[2, 5],
    )
    message.answer.assert_awaited_once()
    reply = message.answer.await_args.args[0]
    assert "✅ Группа привязана" in reply
    assert "2, 5" in reply


@pytest.mark.asyncio
async def test_register_group_private_replies_group_only_hint() -> None:
    message = _make_message(chat_type=ChatType.PRIVATE, text="/register_group")

    await cmd_group_commands_private_only(message)

    message.answer.assert_awaited_once()
    reply = message.answer.await_args.args[0]
    assert "только в группе" in reply.lower()
    assert "/register_group" in reply


@pytest.mark.asyncio
async def test_unregister_group_private_replies_group_only_hint() -> None:
    message = _make_message(chat_type=ChatType.PRIVATE, text="/unregister_group")

    await cmd_group_commands_private_only(message)

    message.answer.assert_awaited_once()
    reply = message.answer.await_args.args[0]
    assert "только в группе" in reply.lower()
    assert "/unregister_group" in reply


@pytest.mark.asyncio
async def test_unregister_group_in_group_replies_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _make_message(chat_type=ChatType.GROUP, text="/unregister_group")
    session = AsyncMock()
    group = TelegramGroup(
        id=1,
        chat_id=message.chat.id,
        title="Test Group",
        category_ids=None,
        is_active=False,
    )
    deactivate_mock = AsyncMock(return_value=group)
    monkeypatch.setattr(
        "app.bot.handlers.admin_groups.group_posting_service.deactivate_telegram_group",
        deactivate_mock,
    )

    await cmd_unregister_group(message, session)

    deactivate_mock.assert_awaited_once_with(session, message.chat.id)
    message.answer.assert_awaited_once()
    reply = message.answer.await_args.args[0]
    assert "отключена" in reply.lower()
