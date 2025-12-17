"""Application configuration using pydantic-settings."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Authentication
    api_key: str = "change-me-in-production"

    # Temporary file storage
    temp_dir: Path = Path("/tmp/subtitle-service")

    # Video constraints
    max_video_duration: int = 60  # seconds

    # Logging
    log_level: str = "INFO"

    # App info
    app_name: str = "Subtitle Microservice"
    app_version: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
