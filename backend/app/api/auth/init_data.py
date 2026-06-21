import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status


class InitDataError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def validate_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 86400) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InitDataError("Missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise InitDataError("Invalid initData")

    auth_date_raw = parsed.get("auth_date")
    if auth_date_raw is None:
        raise InitDataError("Missing auth_date")
    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise InitDataError("Invalid auth_date") from exc
    if time.time() - auth_date > max_age_seconds:
        raise InitDataError("initData expired")

    user_raw = parsed.get("user")
    if not user_raw:
        raise InitDataError("Missing user")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("Invalid user payload") from exc
    if "id" not in user:
        raise InitDataError("Missing user id")

    return user
