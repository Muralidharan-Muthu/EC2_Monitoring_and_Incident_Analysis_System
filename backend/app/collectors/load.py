"""Remote System Load collector via SSH."""

from __future__ import annotations

from typing import Any
from app.ssh.models import CommandResult


async def collect_load(session) -> dict[str, Any]:
    """
    Collect 1m, 5m, 15m system load averages from /proc/loadavg.

    Returns None for any unmeasured load value. Never returns 0.0 as fallback.
    """
    result: dict[str, Any] = {
        "load_1m": None,
        "load_5m": None,
        "load_15m": None,
        "status": "failed",
        "error": None,
    }

    cmd_res: CommandResult = await session.execute("cat /proc/loadavg")
    if not cmd_res.success or not cmd_res.stdout:
        result["error"] = cmd_res.error or "Failed to read /proc/loadavg."
        return result

    # Format: 0.15 0.08 0.06 1/142 12345
    tokens = cmd_res.stdout.strip().split()
    if len(tokens) >= 3:
        try:
            result["load_1m"] = round(float(tokens[0]), 2)
            result["load_5m"] = round(float(tokens[1]), 2)
            result["load_15m"] = round(float(tokens[2]), 2)
            result["status"] = "success"
            return result
        except ValueError as exc:
            result["error"] = f"Failed to parse load values: {exc}"
            return result

    result["error"] = "Unexpected format in /proc/loadavg"
    return result
