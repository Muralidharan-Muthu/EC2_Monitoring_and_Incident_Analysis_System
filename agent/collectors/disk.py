"""Disk usage metrics collector."""

from __future__ import annotations

import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def collect_disk(mount_point: str = "/") -> dict:
    """
    Collect disk usage for the specified mount point.

    Defaults to the root filesystem. On EC2 Linux, this is typically
    the primary EBS volume.

    Returns:
        dict with disk_usage (%), disk_free_gb.
    """
    result = {
        "disk_usage": 0.0,
        "disk_free_gb": 0.0,
    }

    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, disk metrics unavailable")
        return result

    try:
        disk = psutil.disk_usage(mount_point)
        result["disk_usage"] = disk.percent
        result["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
    except FileNotFoundError:
        logger.warning("disk_mount_not_found: %s", mount_point)
    except Exception as exc:
        logger.warning("disk_collection_failed: %s", exc)

    return result
