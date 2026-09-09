"""Remote Disk metrics collector via SSH."""

from __future__ import annotations

from typing import Any
from app.ssh.models import CommandResult


async def collect_disk(session, mount_point: str = "/") -> dict[str, Any]:
    """
    Collect root filesystem disk metrics from remote EC2 instance using `df -P /`.

    Returns usage percent and storage breakdown in GB.
    Returns None if command fails or cannot be parsed.
    """
    result: dict[str, Any] = {
        "disk_usage": None,
        "disk_total_gb": None,
        "disk_used_gb": None,
        "disk_free_gb": None,
        "status": "failed",
        "error": None,
    }

    cmd = f"df -P {mount_point}"
    cmd_res: CommandResult = await session.execute(cmd)
    if not cmd_res.success or not cmd_res.stdout:
        result["error"] = cmd_res.error or f"Command '{cmd}' failed or produced empty output."
        return result

    # Example POSIX output:
    # Filesystem     1024-blocks    Used Available Capacity Mounted on
    # /dev/root          7186416 3524816   3645216      50% /
    lines = cmd_res.stdout.strip().splitlines()
    if len(lines) >= 2:
        data_line = lines[1].strip()
        parts = data_line.split()
        if len(parts) >= 5:
            try:
                # 1024-byte blocks to GB: blocks / (1024 * 1024)
                total_kb = float(parts[1])
                used_kb = float(parts[2])
                avail_kb = float(parts[3])
                cap_str = parts[4].replace("%", "").strip()

                gb_factor = 1024.0 * 1024.0
                result["disk_total_gb"] = round(total_kb / gb_factor, 2)
                result["disk_used_gb"] = round(used_kb / gb_factor, 2)
                result["disk_free_gb"] = round(avail_kb / gb_factor, 2)
                result["disk_usage"] = round(float(cap_str), 2)
                result["status"] = "success"
                return result
            except (ValueError, IndexError) as exc:
                result["error"] = f"Failed to parse df numbers: {exc}"
                return result

    result["error"] = "Unexpected df -P output format."
    return result
