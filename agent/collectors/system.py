"""
System information collector.

Collects hostname, OS name, and kernel version.
"""

from __future__ import annotations

import logging
import platform
import socket

logger = logging.getLogger(__name__)


def collect_system_info() -> dict:
    """
    Collect system identification information.

    Returns:
        dict with hostname, os_name, kernel_version.
    """
    result = {
        "hostname": "unknown",
        "os_name": None,
        "kernel_version": None,
    }

    try:
        result["hostname"] = socket.gethostname()
    except Exception as exc:
        logger.warning("hostname_collection_failed: %s", exc)

    try:
        result["os_name"] = f"{platform.system()} {platform.release()}"
        result["kernel_version"] = platform.version()
    except Exception as exc:
        logger.warning("os_info_collection_failed: %s", exc)

    return result
