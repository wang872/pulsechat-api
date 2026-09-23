from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PulseChat"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 720
    database_url: str = "sqlite:///./data/pulsechat.db"
    algorithm: str = "HS256"
    seed_on_startup: bool = True
    rate_limit_messages: int = 5
    rate_limit_window_seconds: float = 2.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
