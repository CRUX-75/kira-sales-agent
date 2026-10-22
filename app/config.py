"""Environment-based settings. Production values belong in the deployment environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "kira-sales-agent"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    wording_provider: str = "none"  # none | openai | anthropic
    wording_model: str = ""  # empty = provider default
    wording_effort: str = "low"
    wording_timeout_seconds: float = 8.0
    database_url: str | None = None
    session_ttl_days: int = 7  # data minimisation: older sessions are purged
    whatsapp_sending_enabled: bool = False  # emergency stop: default is OFF


@lru_cache
def get_settings() -> Settings:
    return Settings()
