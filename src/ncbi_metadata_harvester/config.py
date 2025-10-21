"""Configuration management using environment variables."""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # NCBI E-utilities configuration
    ncbi_tool: str = "ncbi-metadata-harvester"
    ncbi_email: str = "user@example.com"
    ncbi_api_key: str | None = None

    # Rate limiting (requests per second)
    # NCBI allows 3 rps without API key, 10 rps with API key
    ncbi_rate_limit: float = 3.0  # Override to 10.0 when using API key

    # Retry configuration
    max_retries: int = 3
    retry_base_delay: float = 0.5  # seconds
    retry_max_delay: float = 8.0  # seconds


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
