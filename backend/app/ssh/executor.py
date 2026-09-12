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

    # Check allowlist prefixes
    for prefix in ALLOWED_COMMAND_PREFIXES:
        if cmd.startswith(prefix):
            return True, "Command allowed."

    return False, f"Command '{cmd[:40]}' is not in the monitoring allowlist."


ALLOWED_REMEDIATION_PREFIXES: tuple[str, ...] = (
    "pkill",
    "killall",
    "kill",
    "rm -f /var/tmp/",
    "rm -f /tmp/",
    "sync",
    "ps -eo",
    "ps -e",
    "free -m",
    "free -h",
    "free",
    "df -h",
    "df",
    "du -sh",
    "du -h",
    "journalctl",
    "uptime",
)

# Forbidden dangerous tokens for remediation commands
FORBIDDEN_REMEDIATION_TOKENS: tuple[str, ...] = (
    "rm -rf /",
    "rm -rf *",
    "shutdown",
    "reboot",
    "poweroff",
    "init ",
    "mkfs",
    "dd ",
    "curl",
    "wget",
    "nc ",
    "eval",
    "exec",
    "> /dev/sd",
    "> /dev/nvme",
    "> /dev/vd",
    "> /dev/xvd",
    ":(){",
)


def is_remediation_command_allowed(command: str) -> Tuple[bool, str]:
    """
    Validate that an operational remediation command is safe to execute on the EC2 host.
    Permits process termination, cache flushing, disk cleanup, and diagnostics.
    """
    cmd = command.strip()
    if not cmd:
        return False, "Remediation command cannot be empty."

    # Strip optional sudo prefix for validation
    normalized = cmd[5:].strip() if cmd.startswith("sudo ") else cmd

    # Check for dangerous tokens
    for token in FORBIDDEN_REMEDIATION_TOKENS:
        if token in normalized:
            return False, f"Remediation command contains forbidden token: '{token}'."

    # Check allowlist prefixes
    for prefix in ALLOWED_REMEDIATION_PREFIXES:
        if normalized.startswith(prefix):
            return True, "Remediation command allowed."

    return False, f"Remediation command '{normalized[:40]}' is not in the approved operational list."

