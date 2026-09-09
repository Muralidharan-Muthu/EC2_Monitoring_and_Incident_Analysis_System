"""Remote Log collector via SSH."""

from __future__ import annotations

import re
from typing import Any
from app.ssh.models import CommandResult


async def collect_logs(session, limit: int = 20) -> dict[str, Any]:
    """
    Collect recent system logs using journalctl.

    Attempts priority warning..err first for incident diagnostics,
    falling back to general logs if no warnings are found.
    Handles permission issues gracefully without interpreting missing logs as 'no errors'.
    """
    result: dict[str, Any] = {
        "logs": [],
        "status": "failed",
        "error": None,
    }

    # Attempt warning..err first
    cmd = f"journalctl -p warning..err -n {limit} --no-pager"
    cmd_res: CommandResult = await session.execute(cmd)

    if not cmd_res.success:
        if "permission" in (cmd_res.stderr or "").lower():
            result["status"] = "permission_denied"
            result["error"] = "Insufficient permissions to read system journal."
        else:
            result["error"] = cmd_res.error or "Failed to run journalctl."
        return result

    lines = [ln.strip() for ln in cmd_res.stdout.splitlines() if ln.strip()]
    if not lines or "-- No entries --" in cmd_res.stdout:
        # Fall back to general recent logs
        fallback_cmd = f"journalctl -n {limit} --no-pager"
        fb_res: CommandResult = await session.execute(fallback_cmd)
        if fb_res.success and fb_res.stdout:
            lines = [ln.strip() for ln in fb_res.stdout.splitlines() if ln.strip()]

    parsed_logs: list[dict[str, str]] = []
    # Standard journalctl line format:
    # Sep 09 10:45:01 hostname systemd[1]: Started Session 123 of user ubuntu.
    log_pattern = re.compile(r"^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+([^\s]+)\s+([^:]+):\s*(.*)$")

    for line in lines:
        if line.startswith("--") and line.endswith("--"):
            continue
        match = log_pattern.match(line)
        if match:
            ts, host, source, msg = match.groups()
            parsed_logs.append({
                "timestamp": ts,
                "priority": "warning" if "warning" in cmd else "info",
                "message": f"[{source}] {msg}",
            })
        else:
            # Unstructured single line
            parsed_logs.append({
                "timestamp": "",
                "priority": "info",
                "message": line,
            })

    result["logs"] = parsed_logs[-limit:]
    result["status"] = "success"
    return result
