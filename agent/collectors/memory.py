"""Memory metrics collector."""

from __future__ import annotations

import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def collect_memory() -> dict:
    """
    Collect memory usage metrics.

    Returns:
        dict with memory_usage (%), memory_available_mb.
    """
    result = {
        "memory_usage": 0.0,
        "memory_available_mb": 0.0,
    }

    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, memory metrics unavailable")
        return result

    try:
        mem = psutil.virtual_memory()
        result["memory_usage"] = mem.percent
        result["memory_available_mb"] = round(mem.available / (1024 * 1024), 1)
    except Exception as exc:
        logger.warning("memory_collection_failed: %s", exc)

    return result
