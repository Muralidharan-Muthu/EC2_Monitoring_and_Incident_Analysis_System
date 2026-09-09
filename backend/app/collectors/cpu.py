"""Remote CPU metrics collector via SSH."""

from __future__ import annotations

import re
from typing import Any, Optional
from app.ssh.models import CommandResult


async def collect_cpu(session) -> dict[str, Any]:
    """
    Collect CPU usage and core count from remote EC2 instance.

    Uses `mpstat 1 1` for accurate measurement, and `nproc` for core count.
    Never returns 0.0 as a fallback on failure — returns None.
    """
    result: dict[str, Any] = {
        "cpu_usage": None,
        "cpu_count": None,
        "status": "failed",
        "error": None,
    }

    # 1. Core count via nproc
    nproc_res: CommandResult = await session.execute("nproc")
    if nproc_res.success and nproc_res.stdout.strip().isdigit():
        result["cpu_count"] = int(nproc_res.stdout.strip())

    # 2. CPU utilization via mpstat 1 1
    mpstat_res: CommandResult = await session.execute("mpstat 1 1")
    if mpstat_res.success and mpstat_res.stdout:
        # Looking for the Average line: Average: all %usr %nice %sys ... %idle
        for line in mpstat_res.stdout.splitlines():
            line_clean = line.strip()
            if "Average:" in line_clean and ("all" in line_clean or "ALL" in line_clean):
                tokens = line_clean.split()
                try:
                    idle_val = float(tokens[-1])
                    usage_val = round(max(0.0, min(100.0, 100.0 - idle_val)), 2)
                    result["cpu_usage"] = usage_val
                    result["status"] = "success"
                    return result
                except (ValueError, IndexError):
                    pass

    # 3. Fallback: Parse /proc/stat if mpstat is unavailable
    stat_res: CommandResult = await session.execute("cat /proc/stat")
    if stat_res.success and stat_res.stdout:
        first_line = stat_res.stdout.splitlines()[0]
        if first_line.startswith("cpu "):
            parts = [float(x) for x in first_line.split()[1:] if x.isdigit()]
            if len(parts) >= 4:
                idle = parts[3]
                total = sum(parts)
                if total > 0:
                    # Note: Instantaneous snapshot from /proc/stat is cumulative since boot
                    usage = round((1.0 - (idle / total)) * 100.0, 2)
                    result["cpu_usage"] = max(0.0, min(100.0, usage))
                    result["status"] = "success"
                    return result

    result["error"] = mpstat_res.error or "Failed to parse mpstat or /proc/stat output"
    return result
