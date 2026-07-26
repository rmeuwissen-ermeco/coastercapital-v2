from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Coaster Capital API"
    environment: str = "development"
    api_version: str = "0.1.0"

    model_config = SettingsConfigDict(env_prefix="COASTER_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

