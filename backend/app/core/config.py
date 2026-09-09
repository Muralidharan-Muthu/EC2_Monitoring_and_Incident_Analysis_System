"""
Application configuration loaded from environment variables.

All settings are defined here to avoid scattered os.getenv() calls
throughout the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = Field(default="EC2 Monitoring System")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/ec2monitor"
    )
    supabase_host: str = Field(default="")
    supabase_port: int = Field(default=6543)
    supabase_db: str = Field(default="postgres")
    supabase_user: str = Field(default="")
    supabase_password: str = Field(default="")
    supabase_schema: str = Field(default="ec2_monitoring_working")
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="")

    # ---- Groq LLM ----
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # ---- Security ----
    monitoring_agent_api_key: str = Field(default="")

    # ---- CORS ----
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ---- Anomaly Detection Thresholds ----
    cpu_warning_threshold: float = Field(default=70.0)
    cpu_critical_threshold: float = Field(default=90.0)
    memory_warning_threshold: float = Field(default=75.0)
    memory_critical_threshold: float = Field(default=90.0)
    disk_warning_threshold: float = Field(default=80.0)
    disk_critical_threshold: float = Field(default=90.0)

    # ---- Anomaly Persistence ----
    anomaly_consecutive_samples: int = Field(default=3)

    # ---- Correlation Engine ----
    correlation_window_minutes: int = Field(default=5)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
