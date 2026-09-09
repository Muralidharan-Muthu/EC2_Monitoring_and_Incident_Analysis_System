"""Remote Process collector via SSH."""

from __future__ import annotations

from typing import Any
from app.ssh.models import CommandResult


async def collect_processes(session, limit: int = 10) -> dict[str, Any]:
    """
    Collect top CPU and memory consuming processes from EC2 via `ps`.

    Returns a list of structured process dicts.
    Returns empty list on failure, never fake process entries.
    """
    result: dict[str, Any] = {
        "processes": [],
        "status": "failed",
        "error": None,
    }

    # Collect top CPU
    cmd_cpu = "ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 11"
    cpu_res: CommandResult = await session.execute(cmd_cpu)

    # Collect top Memory
    cmd_mem = "ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 11"
    mem_res: CommandResult = await session.execute(cmd_mem)

    if not cpu_res.success and not mem_res.success:
        result["error"] = cpu_res.error or mem_res.error or "Failed to execute ps commands."
        return result

    processes_by_pid: dict[int, dict[str, Any]] = {}

    def _parse_ps_output(stdout: str):
        lines = stdout.strip().splitlines()
        for line in lines[1:]:  # Skip header: PID COMMAND %CPU %MEM
            parts = line.strip().split(None, 3)
            if len(parts) >= 4:
                try:
                    pid = int(parts[0])
                    name = parts[1]
                    cpu_p = float(parts[2])
                    mem_p = float(parts[3])
                    if pid not in processes_by_pid:
                        processes_by_pid[pid] = {
                            "pid": pid,
                            "name": name,
                            "cpu_percent": round(cpu_p, 1),
                            "memory_percent": round(mem_p, 1),
                        }
                    else:
                        # Update with any more recent/accurate numbers
                        processes_by_pid[pid]["cpu_percent"] = max(processes_by_pid[pid]["cpu_percent"], round(cpu_p, 1))
                        processes_by_pid[pid]["memory_percent"] = max(processes_by_pid[pid]["memory_percent"], round(mem_p, 1))
                except (ValueError, IndexError):
                    continue

    if cpu_res.success and cpu_res.stdout:
        _parse_ps_output(cpu_res.stdout)

    if mem_res.success and mem_res.stdout:
        _parse_ps_output(mem_res.stdout)

    # Sort primarily by CPU descending, then memory descending
    sorted_procs = sorted(
        processes_by_pid.values(),
        key=lambda p: (p["cpu_percent"], p["memory_percent"]),
        reverse=True,
    )[:limit]

    result["processes"] = sorted_procs
    result["status"] = "success"
    return result
