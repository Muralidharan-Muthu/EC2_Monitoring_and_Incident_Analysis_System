"""
CPU metrics collector.

Uses psutil for cross-platform compatibility and supplements with
Linux /proc data where available.
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def collect_cpu() -> dict:
    """
    Collect CPU usage metrics.

    Returns:
        dict with cpu_usage, cpu_count, and load averages.
    """
    result = {
        "cpu_usage": 0.0,
        "cpu_count": 1,
        "load_1m": 0.0,
        "load_5m": 0.0,
        "load_15m": 0.0,
    }

    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, CPU metrics unavailable")
        return result

    try:
        # interval=1 gives a blocking 1-second measurement for accuracy
        result["cpu_usage"] = psutil.cpu_percent(interval=1)
        result["cpu_count"] = psutil.cpu_count(logical=True) or 1
    except Exception as exc:
        logger.warning("cpu_usage_collection_failed: %s", exc)

    try:
        load = psutil.getloadavg()
        result["load_1m"] = round(load[0], 2)
        result["load_5m"] = round(load[1], 2)
        result["load_15m"] = round(load[2], 2)
    except (AttributeError, OSError) as exc:
        # getloadavg() is not available on Windows
        logger.debug("load_average_unavailable: %s", exc)

    return result
