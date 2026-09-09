"""Remote Network metrics collector via SSH."""

from __future__ import annotations

from typing import Any
from app.ssh.models import CommandResult


async def collect_network(session) -> dict[str, Any]:
    """
    Collect aggregate received and transmitted bytes across non-loopback network interfaces
    from /proc/net/dev.

    Returns None if command fails or cannot be parsed. Never fabricates 0.
    """
    result: dict[str, Any] = {
        "network_rx_bytes": None,
        "network_tx_bytes": None,
        "status": "failed",
        "error": None,
    }

    cmd_res: CommandResult = await session.execute("cat /proc/net/dev")
    if not cmd_res.success or not cmd_res.stdout:
        result["error"] = cmd_res.error or "Failed to read /proc/net/dev."
        return result

    lines = cmd_res.stdout.strip().splitlines()
    # Lines 0 and 1 are headers:
    # Inter-|   Receive                                                |  Transmit
    #  face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    total_rx = 0
    total_tx = 0
    interfaces_found = 0

    for line in lines:
        if ":" not in line:
            continue
        iface, data = line.split(":", 1)
        iface = iface.strip()
        if iface == "lo":
            # Exclude loopback
            continue

        parts = data.split()
        # parts[0] is rx bytes, parts[8] is tx bytes
        if len(parts) >= 9:
            try:
                rx = int(parts[0])
                tx = int(parts[8])
                total_rx += rx
                total_tx += tx
                interfaces_found += 1
            except ValueError:
                continue

    if interfaces_found > 0:
        result["network_rx_bytes"] = total_rx
        result["network_tx_bytes"] = total_tx
        result["status"] = "success"
        return result

    result["error"] = "No non-loopback network interfaces found in /proc/net/dev."
    return result
