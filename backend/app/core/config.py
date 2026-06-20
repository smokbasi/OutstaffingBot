from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    webhook_secret: str = ""
    webhook_url: str = ""

    database_url: str = "postgresql+asyncpg://outstaffing:outstaffing@localhost:5432/outstaffing"
    redis_url: str = "redis://localhost:6379/0"

    mini_app_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    admin_telegram_ids: list[int] = Field(default_factory=list)

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
