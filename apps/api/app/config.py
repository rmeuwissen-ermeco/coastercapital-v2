from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Coaster Capital API"
    environment: str = "development"
    api_version: str = "0.1.0"
    database_url: str = "sqlite:///./coastercapital.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    auto_create_schema: bool = True
    jwt_secret: str = "development-only-secret-change-me"
    access_token_minutes: int = 480
    admin_email: str | None = None
    admin_password: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6"
    research_timeout_seconds: float = 25.0
    research_max_page_bytes: int = 1_500_000

    @field_validator("database_url", mode="before")
    @classmethod
    def select_psycopg_driver(cls, value: object) -> object:
        """Make provider PostgreSQL URLs use the installed psycopg 3 driver."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    model_config = SettingsConfigDict(
        env_prefix="COASTER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
