"""
Process metrics collector.

Identifies the top CPU and memory consuming processes at the time
of collection. Used as evidence during incident analysis.
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


def _safe_process_info(proc) -> Optional[dict]:
    """Safely extract process info, handling AccessDenied and NoSuchProcess."""
    try:
        with proc.oneshot():
            return {
                "name": proc.name(),
                "pid": proc.pid,
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": round(proc.memory_percent(), 2),
            }
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    except Exception as exc:
        logger.debug("process_info_error pid=%s: %s", getattr(proc, 'pid', '?'), exc)
        return None


def collect_processes() -> dict:
    """
    Collect information about top resource-consuming processes.

    Returns:
        dict with top_cpu_process, top_cpu_percent, top_cpu_pid,
                    top_memory_process, top_memory_percent, top_memory_pid.
    """
    result = {
        "top_cpu_process": None,
        "top_cpu_percent": None,
        "top_cpu_pid": None,
        "top_memory_process": None,
        "top_memory_percent": None,
        "top_memory_pid": None,
    }

    if not PSUTIL_AVAILABLE:
        return result

    try:
        # First pass: collect cpu_percent (starts measurement)
        procs = []
        for proc in psutil.process_iter(["name", "pid"]):
            info = _safe_process_info(proc)
            if info:
                procs.append(info)

        if not procs:
            return result

        # Sort by CPU
        by_cpu = sorted(procs, key=lambda p: p["cpu_percent"] or 0, reverse=True)
        if by_cpu:
            top_cpu = by_cpu[0]
            result["top_cpu_process"] = top_cpu["name"]
            result["top_cpu_percent"] = round(top_cpu["cpu_percent"], 2)
            result["top_cpu_pid"] = top_cpu["pid"]

        # Sort by memory
        by_mem = sorted(procs, key=lambda p: p["memory_percent"] or 0, reverse=True)
        if by_mem:
            top_mem = by_mem[0]
            result["top_memory_process"] = top_mem["name"]
            result["top_memory_percent"] = round(top_mem["memory_percent"], 2)
            result["top_memory_pid"] = top_mem["pid"]

    except Exception as exc:
        logger.warning("process_collection_failed: %s", exc)

    return result
