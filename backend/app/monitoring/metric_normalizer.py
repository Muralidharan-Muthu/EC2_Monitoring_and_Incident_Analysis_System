"""
Metric normalizer service.
Transforms raw collector outputs into a UnifiedSnapshot and DB-ready models.
Strictly preserves None for missing or unmeasured data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.schemas.monitoring import (
    CPUInfo,
    DataQuality,
    DiskInfo,
    LoadInfo,
    LogEntry,
    MemoryInfo,
    NetworkInfo,
    ProcessItem,
    ResponseTimeInfo,
    SystemInfo,
    UnifiedSnapshot,
)


def normalize_to_unified_snapshot(
    raw_results: Dict[str, Any],
    collection_errors: Optional[List[str]] = None,
) -> UnifiedSnapshot:
    """
    Construct a UnifiedSnapshot from individual collector outputs.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    errors: List[str] = list(collection_errors or [])

    # 1. CPU
    cpu_raw = raw_results.get("cpu", {})
    cpu_info = CPUInfo(
        usage_percent=cpu_raw.get("cpu_usage"),
        count=cpu_raw.get("cpu_count"),
    )
    if cpu_raw.get("error"):
        errors.append(f"CPU: {cpu_raw['error']}")

    # 2. Memory
    mem_raw = raw_results.get("memory", {})
    mem_info = MemoryInfo(
        usage_percent=mem_raw.get("memory_usage"),
        total_mb=mem_raw.get("memory_total_mb"),
        used_mb=mem_raw.get("memory_used_mb"),
        available_mb=mem_raw.get("memory_available_mb"),
    )
    if mem_raw.get("error"):
        errors.append(f"Memory: {mem_raw['error']}")

    # 3. Disk
    disk_raw = raw_results.get("disk", {})
    disk_info = DiskInfo(
        usage_percent=disk_raw.get("disk_usage"),
        total_gb=disk_raw.get("disk_total_gb"),
        used_gb=disk_raw.get("disk_used_gb"),
        free_gb=disk_raw.get("disk_free_gb"),
    )
    if disk_raw.get("error"):
        errors.append(f"Disk: {disk_raw['error']}")

    # 4. Load
    load_raw = raw_results.get("load", {})
    load_info = LoadInfo(
        load_1m=load_raw.get("load_1m"),
        load_5m=load_raw.get("load_5m"),
        load_15m=load_raw.get("load_15m"),
    )
    if load_raw.get("error"):
        errors.append(f"Load: {load_raw['error']}")

    # 5. Network
    net_raw = raw_results.get("network", {})
    net_info = NetworkInfo(
        rx_bytes=net_raw.get("network_rx_bytes"),
        tx_bytes=net_raw.get("network_tx_bytes"),
    )
    if net_raw.get("error"):
        errors.append(f"Network: {net_raw['error']}")

    # 6. Processes
    proc_raw = raw_results.get("process", {})
    processes: List[ProcessItem] = []
    for p in proc_raw.get("processes", []):
        processes.append(
            ProcessItem(
                pid=p.get("pid"),
                name=p.get("name", "unknown"),
                cpu_percent=p.get("cpu_percent"),
                memory_percent=p.get("memory_percent"),
            )
        )
    if proc_raw.get("error"):
        errors.append(f"Processes: {proc_raw['error']}")

    # 7. Logs
    logs_raw = raw_results.get("logs", {})
    logs: List[LogEntry] = []
    for lg in logs_raw.get("logs", []):
        logs.append(
            LogEntry(
                timestamp=lg.get("timestamp", ""),
                priority=lg.get("priority", "info"),
                message=lg.get("message", ""),
            )
        )
    if logs_raw.get("error"):
        errors.append(f"Logs: {logs_raw['error']}")

    # 8. Response Time
    resp_raw = raw_results.get("response_time", {})
    resp_info = ResponseTimeInfo(
        ms=resp_raw.get("response_time_ms"),
        http_status=resp_raw.get("http_status"),
        enabled=bool(resp_raw.get("response_time_enabled", False)),
        url=resp_raw.get("url"),
    )
    if resp_raw.get("error"):
        errors.append(f"ResponseTime: {resp_raw['error']}")

    # 9. System Info
    sys_raw = raw_results.get("system", {})
    sys_info = SystemInfo(
        hostname=sys_raw.get("hostname"),
        os_name=sys_raw.get("os_name"),
        os_version=sys_raw.get("os_version"),
        kernel_version=sys_raw.get("kernel_version"),
    )
    if sys_raw.get("error"):
        errors.append(f"SystemInfo: {sys_raw['error']}")

    # Collector statuses
    collector_status = {
        "cpu": cpu_raw.get("status", "failed"),
        "memory": mem_raw.get("status", "failed"),
        "disk": disk_raw.get("status", "failed"),
        "load": load_raw.get("status", "failed"),
        "process": proc_raw.get("status", "failed"),
        "network": net_raw.get("status", "failed"),
        "logs": logs_raw.get("status", "failed"),
        "response_time": resp_raw.get("status", "disabled"),
        "system": sys_raw.get("status", "failed"),
    }

    # Data quality calculation
    # Critical collectors to determine overall quality:
    critical_collectors = ["cpu", "memory", "disk", "load", "process", "network"]
    successes = sum(1 for c in critical_collectors if collector_status.get(c) == "success")
    failures = sum(1 for c in critical_collectors if collector_status.get(c) != "success")

    if failures == 0:
        dq_status = "COMPLETE"
    elif successes > 0:
        dq_status = "PARTIAL"
    else:
        dq_status = "FAILED"

    data_quality = DataQuality(
        collection_status=dq_status,
        successful_collectors=successes,
        failed_collectors=failures,
        errors=errors,
    )

    hostname = sys_info.hostname or "unknown"

    return UnifiedSnapshot(
        timestamp=now_iso,
        hostname=hostname,
        cpu=cpu_info,
        memory=mem_info,
        disk=disk_info,
        load=load_info,
        network=net_info,
        processes=processes,
        logs=logs,
        response_time=resp_info,
        system=sys_info,
        collector_status=collector_status,
        collection_errors=errors,
        data_quality=data_quality,
    )
