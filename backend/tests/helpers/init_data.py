import hashlib
import hmac
import json
import time
from urllib.parse import urlencode


def build_test_init_data(
    bot_token: str,
    user_id: int,
    *,
    username: str = "testuser",
    first_name: str = "Test",
    auth_date: int | None = None,
) -> str:
    user = json.dumps(
        {"id": user_id, "first_name": first_name, "username": username},
        separators=(",", ":"),
    )
    payload = {
        "user": user,
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)
