"""
Linux log collector.

Reads recent error/warning entries from systemd journal.
Uses only safe, pre-approved commands via subprocess.
"""

from __future__ import annotations

import logging
import subprocess
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

# Allowlist of commands that may be executed
ALLOWED_COMMANDS = {"journalctl", "dmesg"}


def _run_safe(cmd: list[str], timeout: int = 5) -> Optional[str]:
    """
    Run a command from the allowlist and return stdout.

    Returns None on any error.
    """
    if not cmd:
        return None
    if cmd[0] not in ALLOWED_COMMANDS:
        logger.warning("blocked_command: %s", cmd[0])
        return None
    if not shutil.which(cmd[0]):
        logger.debug("command_not_found: %s", cmd[0])
        return None

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Do not raise on non-zero exit
        )
        return result.stdout.strip() or None
    except subprocess.TimeoutExpired:
        logger.warning("command_timeout: %s", " ".join(cmd))
        return None
    except PermissionError:
        logger.debug("command_permission_denied: %s", cmd[0])
        return None
    except Exception as exc:
        logger.warning("command_error %s: %s", cmd[0], exc)
        return None


def collect_recent_logs(lines: int = 20) -> Optional[str]:
    """
    Collect recent error/warning log entries using journalctl.

    Returns a string with the log lines, or None if unavailable.
    """
    output = _run_safe([
        "journalctl",
        "--no-pager",
        "-n", str(lines),
        "-p", "err",  # Only error priority and above
        "--output=short",
    ])
    return output
