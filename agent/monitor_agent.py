"""
Main monitoring agent.

Entry point for the EC2 monitoring agent.
Runs a periodic collection loop, gathering system metrics and sending
them to the FastAPI backend.

Usage (on the EC2 Linux instance):
    python monitor_agent.py

The agent continues operating even if individual collectors fail.
A single failed collector never stops the agent.
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any

from config import AgentConfig
from sender import send_metrics
from collectors.cpu import collect_cpu
from collectors.memory import collect_memory
from collectors.disk import collect_disk
from collectors.network import collect_network
from collectors.process import collect_processes
from collectors.system import collect_system_info
from collectors.load import collect_response_time
from collectors.logs import collect_recent_logs

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("monitor_agent")


def _safe_collect(name: str, collector_fn, *args, **kwargs) -> dict:
    """
    Safely run a collector function.

    If the collector raises any exception, log the error and return
    an empty dict. The agent continues with other collectors.
    """
    try:
        result = collector_fn(*args, **kwargs)
        return result or {}
    except Exception as exc:
        logger.error("collector_failed name=%s: %s", name, exc)
        return {}


def collect_all_metrics(config: AgentConfig) -> dict[str, Any]:
    """
    Collect all system metrics using individual collector modules.

    Each collector is isolated — failures are caught independently.
    """
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    # System info (hostname, OS)
    sys_info = _safe_collect("system", collect_system_info)

    # Core metrics
    cpu_data = _safe_collect("cpu", collect_cpu)
    mem_data = _safe_collect("memory", collect_memory)
    disk_data = _safe_collect("disk", collect_disk, "/")
    net_data = _safe_collect("network", collect_network)
    proc_data = _safe_collect("process", collect_processes)

    # Optional response-time measurement
    rt_data = _safe_collect("response_time", collect_response_time, config.monitored_url)

    # Build unified payload
    payload: dict[str, Any] = {
        "hostname": sys_info.get("hostname", "unknown"),
        "timestamp": timestamp,

        # Core metrics
        "cpu_usage": cpu_data.get("cpu_usage", 0.0),
        "memory_usage": mem_data.get("memory_usage", 0.0),
        "disk_usage": disk_data.get("disk_usage", 0.0),
        "load_1m": cpu_data.get("load_1m", 0.0),
        "load_5m": cpu_data.get("load_5m", 0.0),
        "load_15m": cpu_data.get("load_15m", 0.0),

        # Supporting
        "cpu_count": cpu_data.get("cpu_count", 1),
        "memory_available_mb": mem_data.get("memory_available_mb"),
        "disk_free_gb": disk_data.get("disk_free_gb"),

        # Network
        "network_rx_bytes": net_data.get("network_rx_bytes"),
        "network_tx_bytes": net_data.get("network_tx_bytes"),

        # Processes
        "top_cpu_process": proc_data.get("top_cpu_process"),
        "top_cpu_percent": proc_data.get("top_cpu_percent"),
        "top_cpu_pid": proc_data.get("top_cpu_pid"),
        "top_memory_process": proc_data.get("top_memory_process"),
        "top_memory_percent": proc_data.get("top_memory_percent"),
        "top_memory_pid": proc_data.get("top_memory_pid"),

        # Response time (optional)
        "response_time_ms": rt_data.get("response_time_ms"),
        "http_status": rt_data.get("http_status"),

        # OS info
        "os_name": sys_info.get("os_name"),
        "kernel_version": sys_info.get("kernel_version"),
    }

    return payload


def run_agent(config: AgentConfig) -> None:
    """
    Main agent loop.

    Collects metrics at the configured interval and sends them
    to the backend. Handles SIGTERM/SIGINT gracefully.
    """
    running = True

    def _handle_signal(signum, frame) -> None:
        nonlocal running
        logger.info("shutdown_signal_received signum=%s", signum)
        running = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(
        "agent_started backend=%s interval=%ds",
        config.backend_url,
        config.collection_interval,
    )

    while running:
        start = time.monotonic()

        try:
            payload = collect_all_metrics(config)
            logger.debug(
                "collected hostname=%s cpu=%.1f%% mem=%.1f%%",
                payload["hostname"],
                payload["cpu_usage"],
                payload["memory_usage"],
            )
            success = send_metrics(payload, config)
            if not success:
                logger.warning("metric_delivery_failed — will retry next cycle")
        except Exception as exc:
            logger.error("collection_loop_error: %s", exc)

        elapsed = time.monotonic() - start
        sleep_time = max(0, config.collection_interval - elapsed)
        if running:
            time.sleep(sleep_time)

    logger.info("agent_stopped")


if __name__ == "__main__":
    config = AgentConfig()
    logging.getLogger().setLevel(config.log_level)
    run_agent(config)
