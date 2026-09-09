"""Asynchronous SSH client for remote AWS EC2 Linux instance monitoring."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncssh

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ssh.executor import is_command_allowed
from app.ssh.models import CommandResult, SSHConnectionStatus

logger = get_logger(__name__)


class EC2SSHClient:
    """
    Secure reusable AsyncSSH client for executing remote Linux monitoring commands.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _get_connection_options(self) -> dict:
        """Build connection options for AsyncSSH."""
        key_path = self.settings.resolved_key_path
        return {
            "host": self.settings.ec2_host,
            "port": self.settings.ec2_port,
            "username": self.settings.ec2_username,
            "client_keys": [key_path] if key_path else [],
            "known_hosts": None,  # Automated testing against dynamic EC2 instances
            "connect_timeout": self.settings.ssh_connect_timeout_seconds,
        }

    async def check_connection(self) -> SSHConnectionStatus:
        """
        Test reachability and authentication with the remote EC2 instance.
        """
        valid_key, key_err = self.settings.validate_ssh_key()
        if not valid_key:
            return SSHConnectionStatus(
                connected=False,
                host=self.settings.ec2_host,
                port=self.settings.ec2_port,
                username=self.settings.ec2_username,
                error=key_err,
            )

        if not self.settings.ec2_host:
            return SSHConnectionStatus(
                connected=False,
                host="",
                port=self.settings.ec2_port,
                username=self.settings.ec2_username,
                error="EC2_HOST is not configured in environment.",
            )

        start = time.perf_counter()
        try:
            opts = self._get_connection_options()
            async with asyncssh.connect(**opts) as conn:
                res = await conn.run("uname -s -r", check=False)
                latency = (time.perf_counter() - start) * 1000.0
                return SSHConnectionStatus(
                    connected=True,
                    host=self.settings.ec2_host,
                    port=self.settings.ec2_port,
                    username=self.settings.ec2_username,
                    latency_ms=round(latency, 2),
                    os_info=res.stdout.strip(),
                )
        except asyncssh.PermissionDenied as exc:
            return SSHConnectionStatus(
                connected=False,
                host=self.settings.ec2_host,
                port=self.settings.ec2_port,
                username=self.settings.ec2_username,
                error=f"SSH authentication failed (check username/key): {exc}",
            )
        except (asyncssh.TimeoutError, asyncio.TimeoutError) as exc:
            return SSHConnectionStatus(
                connected=False,
                host=self.settings.ec2_host,
                port=self.settings.ec2_port,
                username=self.settings.ec2_username,
                error=f"SSH connection timed out after {self.settings.ssh_connect_timeout_seconds}s: {exc}",
            )
        except Exception as exc:
            return SSHConnectionStatus(
                connected=False,
                host=self.settings.ec2_host,
                port=self.settings.ec2_port,
                username=self.settings.ec2_username,
                error=f"SSH connection error: {exc}",
            )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[EC2SSHSession, None]:
        """
        Open a persistent connection for a single collection cycle,
        allowing multiple commands to run over one session.
        """
        valid_key, key_err = self.settings.validate_ssh_key()
        if not valid_key:
            raise ConnectionError(f"Cannot open SSH session: {key_err}")

        opts = self._get_connection_options()
        async with asyncssh.connect(**opts) as conn:
            yield EC2SSHSession(conn, self.settings.ssh_command_timeout_seconds)

    async def execute(self, command: str) -> CommandResult:
        """Execute a single standalone command."""
        allowed, reason = is_command_allowed(command)
        if not allowed:
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                error=f"Security violation: {reason}",
            )

        start = time.perf_counter()
        try:
            async with self.session() as s:
                return await s.execute(command)
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000.0
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                duration_ms=round(duration, 2),
                error=str(exc),
            )


class EC2SSHSession:
    """Active session wrapper reusing an existing connection."""

    def __init__(self, connection: asyncssh.SSHClientConnection, timeout: int) -> None:
        self.connection = connection
        self.timeout = timeout

    async def execute(self, command: str) -> CommandResult:
        """Execute command over the active SSH connection with allowlist check."""
        allowed, reason = is_command_allowed(command)
        if not allowed:
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                error=f"Security violation: {reason}",
            )

        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self.connection.run(command, check=False),
                timeout=float(self.timeout),
            )
            duration = (time.perf_counter() - start) * 1000.0
            return CommandResult(
                command=command,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                exit_code=result.exit_status if result.exit_status is not None else 0,
                success=(result.exit_status == 0),
                duration_ms=round(duration, 2),
                error=None if result.exit_status == 0 else result.stderr.strip(),
            )
        except (asyncio.TimeoutError, asyncssh.TimeoutError) as exc:
            duration = (time.perf_counter() - start) * 1000.0
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                duration_ms=round(duration, 2),
                error=f"Command timed out after {self.timeout}s",
            )
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000.0
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                duration_ms=round(duration, 2),
                error=str(exc),
            )


# Module-level singleton
_default_client: Optional[EC2SSHClient] = None


def get_ssh_client() -> EC2SSHClient:
    """Return singleton EC2SSHClient."""
    global _default_client
    if _default_client is None:
        _default_client = EC2SSHClient()
    return _default_client


def reset_ssh_client() -> None:
    """Reset singleton EC2SSHClient so updated settings take effect."""
    global _default_client
    _default_client = None
