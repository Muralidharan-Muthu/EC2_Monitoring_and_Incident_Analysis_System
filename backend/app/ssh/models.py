"""Data models for SSH command execution and connection health."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CommandResult:
    """Result of an SSH command execution."""

    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    success: bool = False
    duration_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class SSHConnectionStatus:
    """Status of the SSH connection to the remote EC2 instance."""

    connected: bool
    host: str
    port: int
    username: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    os_info: Optional[str] = None

    @property
    def hostname(self) -> str:
        return self.host
