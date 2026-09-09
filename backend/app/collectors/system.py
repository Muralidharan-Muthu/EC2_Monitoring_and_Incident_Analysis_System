"""Remote System Information collector via SSH."""

from __future__ import annotations

import re
from typing import Any
from app.ssh.models import CommandResult


async def collect_system_info(session) -> dict[str, Any]:
    """
    Collect hostname, kernel version, and OS release information from EC2.

    If one field fails, only that field is None.
    """
    result: dict[str, Any] = {
        "hostname": None,
        "os_name": None,
        "os_version": None,
        "kernel_version": None,
        "status": "failed",
        "error": None,
    }

    # 1. Hostname
    h_res: CommandResult = await session.execute("hostname")
    if h_res.success and h_res.stdout:
        result["hostname"] = h_res.stdout.strip()

    # 2. Kernel
    u_res: CommandResult = await session.execute("uname -r")
    if u_res.success and u_res.stdout:
        result["kernel_version"] = u_res.stdout.strip()

    # 3. OS release
    os_res: CommandResult = await session.execute("cat /etc/os-release")
    if os_res.success and os_res.stdout:
        for line in os_res.stdout.splitlines():
            line = line.strip()
            if line.startswith("NAME="):
                result["os_name"] = line.split("=", 1)[1].strip('"\'')
            elif line.startswith("VERSION_ID="):
                result["os_version"] = line.split("=", 1)[1].strip('"\'')

    if result["hostname"] or result["kernel_version"] or result["os_name"]:
        result["status"] = "success"
    else:
        result["error"] = "Failed to collect system info fields."

    return result
