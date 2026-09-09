"""
Network statistics collector.

Collects total bytes received/transmitted since boot.
The backend can compute deltas between observations if needed.
"""

from __future__ import annotations

import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def collect_network() -> dict:
    """
    Collect network I/O statistics.

    Returns:
        dict with network_rx_bytes, network_tx_bytes.
    """
    result = {
        "network_rx_bytes": 0,
        "network_tx_bytes": 0,
    }

    if not PSUTIL_AVAILABLE:
        return result

    try:
        net = psutil.net_io_counters()
        result["network_rx_bytes"] = net.bytes_recv
        result["network_tx_bytes"] = net.bytes_sent
    except Exception as exc:
        logger.warning("network_collection_failed: %s", exc)

    return result
