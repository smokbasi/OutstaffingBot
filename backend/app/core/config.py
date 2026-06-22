from functools import lru_cache

from pydantic import Field, field_validator
from typing import Annotated

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    bot_username: str = "Outstaffing_Work_BOT"
    webhook_secret: str = ""
    webhook_url: str = ""
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    database_url: str = "postgresql+asyncpg://outstaffing:outstaffing@localhost:5432/outstaffing"
    redis_url: str = "redis://localhost:6379/0"

    mini_app_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    admin_telegram_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    moderation_violation_threshold: int = 3
    bot_release_notes: str = ""
    release_notes_file: str = "RELEASE_NOTES.txt"

    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: object) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        return [int(value)]

    @property
    def bot_enabled(self) -> bool:
        return bool(self.bot_token.strip())

    @property
    def webhook_enabled(self) -> bool:
        return bool(self.webhook_url.strip() and self.webhook_secret.strip())

    @property
    def webhook_allowed_updates(self) -> list[str] | None:
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
