"""Remote Memory metrics collector via SSH."""

from __future__ import annotations

from typing import Any
from app.ssh.models import CommandResult


async def collect_memory(session) -> dict[str, Any]:
    """
    Collect memory metrics from remote EC2 instance using `free -m`.

    Calculates memory usage percentage from (total - available) / total.
    Returns None for all values if command or parsing fails.
    """
    result: dict[str, Any] = {
        "memory_usage": None,
        "memory_total_mb": None,
        "memory_available_mb": None,
        "memory_used_mb": None,
        "status": "failed",
        "error": None,
    }

    cmd_res: CommandResult = await session.execute("free -m")
    if not cmd_res.success or not cmd_res.stdout:
        result["error"] = cmd_res.error or "Command 'free -m' failed or produced empty output."
        return result

    # Example output:
    #               total        used        free      shared  buff/cache   available
    # Mem:             908         374         210           2         454         534
    lines = cmd_res.stdout.strip().splitlines()
    for line in lines:
        if line.startswith("Mem:"):
            parts = line.split()
            # Expecting: ['Mem:', total, used, free, shared, buff/cache, available]
            if len(parts) >= 7:
                try:
                    total = float(parts[1])
                    used = float(parts[2])
                    available = float(parts[6])

                    if total > 0:
                        usage = round(((total - available) / total) * 100.0, 2)
                        result["memory_usage"] = max(0.0, min(100.0, usage))
                        result["memory_total_mb"] = total
                        result["memory_used_mb"] = used
                        result["memory_available_mb"] = available
                        result["status"] = "success"
                        return result
                except (ValueError, IndexError) as exc:
                    result["error"] = f"Failed to parse memory numbers: {exc}"
                    return result

    result["error"] = "Could not find 'Mem:' row in free -m output."
    return result
