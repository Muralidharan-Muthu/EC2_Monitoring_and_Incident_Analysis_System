"""Safe command validation and executor for remote monitoring commands."""

from __future__ import annotations

import re
from typing import Tuple

# Explicit allowlist of command prefixes for remote EC2 monitoring
ALLOWED_COMMAND_PREFIXES: tuple[str, ...] = (
    "nproc",
    "mpstat",
    "free",
    "df",
    "uptime",
    "cat /proc/loadavg",
    "cat /proc/stat",
    "cat /proc/meminfo",
    "cat /proc/net/dev",
    "ps -eo",
    "ps -e",
    "ss",
    "journalctl",
    "uname",
    "hostname",
    "cat /etc/os-release",
)

# Dangerous tokens forbidden in monitoring commands
FORBIDDEN_TOKENS: tuple[str, ...] = (
    "rm ",
    "rmdir",
    "shutdown",
    "reboot",
    "poweroff",
    "init ",
    "systemctl stop",
    "systemctl restart",
    "systemctl disable",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "sudo",
    "curl",
    "wget",
    "nc ",
    "chmod",
    "chown",
    "mkfs",
    "dd ",
    ">",
    ">>",
    "eval",
    "exec",
)


def is_command_allowed(command: str) -> Tuple[bool, str]:
    """
    Validate that a command matches the explicit allowlist and contains no forbidden tokens.

    Returns:
        (is_allowed, reason)
    """
    cmd = command.strip()
    if not cmd:
        return False, "Command cannot be empty."

    # Check for forbidden tokens
    for token in FORBIDDEN_TOKENS:
        if token in cmd:
            return False, f"Command contains forbidden token: '{token}'."

    # Check allowlist
    for prefix in ALLOWED_COMMAND_PREFIXES:
        if cmd.startswith(prefix):
            return True, "Command allowed."

    return False, f"Command '{cmd[:40]}' is not in the monitoring allowlist."
