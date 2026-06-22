import pytest

from app.bot.handlers.admin_groups import _format_category_ids, _parse_category_ids


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
