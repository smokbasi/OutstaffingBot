from urllib.parse import urlparse, urlunparse
from uuid import UUID

from app.core.config import Settings


def build_mini_app_url(settings: Settings, path: str) -> str:
    """Join Mini App base URL with a path, preserving base query parameters."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    parsed = urlparse(settings.mini_app_url)
    base_path = parsed.path.rstrip("/")
    combined_path = f"{base_path}{normalized_path}"
    return urlunparse(parsed._replace(path=combined_path))


def vacancy_deep_link(settings: Settings, job_id: UUID) -> str:
    return build_mini_app_url(settings, f"/vacancy/{job_id}")


def job_start_deep_link(settings: Settings, job_id: UUID, *, bot_username: str | None = None) -> str:
    """Telegram bot deep link for group posts (WebApp buttons don't work in groups)."""
    username = (bot_username or settings.bot_username).strip().lstrip("@")
    return f"https://t.me/{username}?start=job_{job_id}"


def parse_job_start_payload(payload: str | None) -> UUID | None:
    if not payload or not payload.startswith("job_"):
        return None
    try:
        return UUID(payload[4:])
    except ValueError:
        return None


def vacancy_telegram_startapp_link(bot_username: str, job_id: UUID) -> str:
    return f"https://t.me/{bot_username}?startapp=vacancy_{job_id}"


def vacancy_apply_callback_data(job_id: UUID) -> str:
    """Inline callback for push/open vacancy in bot (fits Telegram 64-byte limit)."""
    return f"vacopen:{job_id}"

