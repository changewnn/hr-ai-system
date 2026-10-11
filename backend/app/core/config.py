"""Application configuration with environment-aware dotenv layering."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field
from pydantic import model_validator
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
    jwt_algorithm: str = "HS256"
    database_url: str = "postgresql+asyncpg://hr:hr@localhost:5432/hr_system"
    redis_url: str = "redis://localhost:6379/0"

    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v3"
    embedding_dimension: int = Field(default=1024, ge=1)
    embedding_timeout_seconds: int = Field(default=30, ge=1, le=120)
    knowledge_storage_path: str = "data/knowledge"
    knowledge_max_file_mb: int = Field(default=20, ge=1, le=100)
    knowledge_chunk_size: int = Field(default=2400, ge=500, le=8000)
    knowledge_chunk_overlap: int = Field(default=300, ge=0, le=2000)
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = Field(default=30, ge=1, le=120)
    agent_enabled: bool = False
    agent_max_input_chars: int = Field(default=4000, ge=100, le=10000)
    agent_max_context_chunks: int = Field(default=4, ge=1, le=10)
    agent_rate_limit_per_minute: int = Field(default=30, ge=1, le=300)
    agent_sse_rate_limit_per_minute: int = Field(default=10, ge=1, le=60)
    agent_retention_days: int = Field(default=180, ge=30, le=3650)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.app_env.lower() == "production":
            if self.secret_key == "change-me-in-local-env" or len(self.secret_key) < 32:
                raise ValueError("HR_SECRET_KEY must be a random value of at least 32 characters in production")
            if self.debug:
                raise ValueError("HR_DEBUG must be false in production")
        return self


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
