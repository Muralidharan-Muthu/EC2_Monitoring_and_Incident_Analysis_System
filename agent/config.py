"""
Monitoring agent configuration.

All settings loaded from environment variables / .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AgentConfig:
    """Agent runtime configuration from environment variables."""

    backend_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_URL", "http://localhost:8000")
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("MONITORING_AGENT_API_KEY", "")
    )
    collection_interval: int = field(
        default_factory=lambda: int(os.getenv("COLLECTION_INTERVAL_SECONDS", "30"))
    )
    monitored_url: Optional[str] = field(
        default_factory=lambda: os.getenv("MONITORED_URL") or None
    )
    request_timeout: int = field(
        default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )
    retry_wait: int = field(
        default_factory=lambda: int(os.getenv("RETRY_WAIT_SECONDS", "5"))
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )

    @property
    def metrics_endpoint(self) -> str:
        return f"{self.backend_url.rstrip('/')}/api/metrics"

    def __post_init__(self) -> None:
        if not self.backend_url:
            raise ValueError("BACKEND_URL must be set")
