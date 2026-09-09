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

    # ---- Remote EC2 SSH Configuration ----
    ec2_host: str = Field(default="")
    ec2_port: int = Field(default=22)
    ec2_username: str = Field(default="ubuntu")
    ec2_private_key_path: str = Field(default="")
    ssh_connect_timeout_seconds: int = Field(default=10)
    ssh_command_timeout_seconds: int = Field(default=15)

    # ---- Collection Scheduling ----
    collection_interval_seconds: int = Field(default=30)

    # ---- Optional Application Response Time ----
    monitored_url: str = Field(default="")
    response_time_warning_ms: float = Field(default=1000.0)
    response_time_critical_ms: float = Field(default=2000.0)

    # ---- AWS Credentials (for boto3 EC2 auto-discovery) ----
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_region: str = Field(default="ap-south-1")

    # ---- Groq LLM ----
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="qwen/qwen3.8-27b")

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
        upper = v.upper() if v else "INFO"
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper
    @property
    def resolved_key_path(self) -> str:
        """Resolve private key path across working directories."""
        if not self.ec2_private_key_path:
            return ""
        from pathlib import Path
        p = Path(self.ec2_private_key_path)
        if p.is_absolute() and p.is_file():
            return str(p)
        if p.is_file():
            return str(p.resolve())
        parent_candidate = Path("..") / self.ec2_private_key_path
        if parent_candidate.is_file():
            return str(parent_candidate.resolve())
        backend_candidate = Path("backend") / self.ec2_private_key_path
        if backend_candidate.is_file():
            return str(backend_candidate.resolve())
        return str(p)

    def validate_ssh_key(self) -> tuple[bool, str]:
        """Verify that private key exists, is a regular file, and is readable."""
        if not self.ec2_private_key_path:
            return False, "EC2_PRIVATE_KEY_PATH is not configured."
        from pathlib import Path
        key_file = Path(self.resolved_key_path)
        if not key_file.exists():
            return False, f"Private key file not found: {self.ec2_private_key_path}"
        if not key_file.is_file():
            return False, f"Private key path is not a regular file: {self.ec2_private_key_path}"
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                content = f.read(100)
                if not content:
                    return False, "Private key file is empty."
        except PermissionError:
            return False, "Permission denied reading private key file."
        except Exception as exc:
            return False, f"Error reading private key file: {exc}"
        return True, "Key file is valid and readable."


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
