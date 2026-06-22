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
