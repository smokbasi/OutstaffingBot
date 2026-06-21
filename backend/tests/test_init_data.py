import time

import pytest

from app.api.auth.init_data import InitDataError, validate_init_data
from tests.helpers.init_data import build_test_init_data

TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def test_validate_init_data_accepts_valid_payload() -> None:
    init_data = build_test_init_data(TEST_BOT_TOKEN, user_id=42)
    user = validate_init_data(init_data, TEST_BOT_TOKEN)
    assert user["id"] == 42
    assert user["username"] == "testuser"


def test_validate_init_data_rejects_invalid_hash() -> None:
    init_data = build_test_init_data(TEST_BOT_TOKEN, user_id=42) + "tampered"
    with pytest.raises(InitDataError, match="Invalid initData"):
        validate_init_data(init_data, TEST_BOT_TOKEN)


def test_validate_init_data_rejects_expired_auth_date() -> None:
    old_auth_date = int(time.time()) - 90000
    init_data = build_test_init_data(TEST_BOT_TOKEN, user_id=42, auth_date=old_auth_date)
    with pytest.raises(InitDataError, match="expired"):
        validate_init_data(init_data, TEST_BOT_TOKEN)


def test_validate_init_data_rejects_missing_hash() -> None:
    with pytest.raises(InitDataError, match="Missing hash"):
        validate_init_data("user=%7B%7D&auth_date=123", TEST_BOT_TOKEN)
