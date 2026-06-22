import re

PHONE_MAX_LENGTH = 20
_PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-()]{6,19}$")


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > PHONE_MAX_LENGTH:
        raise ValueError(f"Телефон не длиннее {PHONE_MAX_LENGTH} символов")
    if not _PHONE_PATTERN.match(stripped):
        raise ValueError("Некорректный формат телефона")
    return stripped
