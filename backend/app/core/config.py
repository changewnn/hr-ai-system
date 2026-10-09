"""Application configuration with environment-aware dotenv layering."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime settings loaded from dotenv files and environment variables.

    Precedence is handled by pydantic-settings: process environment variables
    override dotenv values, and later dotenv files override earlier files.
    """

    model_config = SettingsConfigDict(
        env_prefix="HR_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "HR AI System API"
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"

    secret_key: str = Field(default="change-me-in-local-env", min_length=16)
    jwt_expire_hours: int = Field(default=8, ge=1, le=168)
    database_url: str = "postgresql+asyncpg://hr:hr@localhost:5432/hr_system"
    redis_url: str = "redis://localhost:6379/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build and cache settings for the current process."""

    app_env = os.getenv("APP_ENV", "development").lower()
    dotenv_files = (
        PROJECT_DIR / ".env",
        PROJECT_DIR / f".env.{app_env}",
        BACKEND_DIR / ".env",
        BACKEND_DIR / f".env.{app_env}",
        PROJECT_DIR / ".env.local",
        BACKEND_DIR / ".env.local",
    )
    return Settings(_env_file=dotenv_files)
