"""
Correlation engine for grouping related anomalies into a unified incident.
Includes deterministic rule-based analysis (probable cause, recommendations, summary).
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from app.models.anomaly import Anomaly

# Correlation score weights per metric
METRIC_WEIGHTS: dict[str, float] = {
    "cpu_usage": 2.5,
    "memory_usage": 2.5,
    "load_1m": 2.0,
    "disk_usage": 1.5,
    "response_time_ms": 2.0,
}

PERSISTENCE_BONUS = 1.0


def compute_correlation_score(anomalies: List[Anomaly]) -> float:
    """
    Compute a correlation score for a set of anomalies.
    Higher score indicates multi-dimensional resource exhaustion.
    """
    score = 0.0
    for a in anomalies:
        weight = METRIC_WEIGHTS.get(a.metric_name, 1.0)
        score += weight
        if a.is_persistent:
            score += PERSISTENCE_BONUS
    return round(score, 2)


def compute_incident_key(hostname: str, affected_metrics: List[str]) -> str:
    """
    Deterministic deduplication key derived from hostname and affected metrics.
    Ensures continuing abnormal conditions update the existing incident rather
    than spawning duplicate incidents.
    """
    # Group core system metrics into a common family if multiple occur together
    metric_set = set(affected_metrics)
    family = "general"
    if {"cpu_usage", "memory_usage"}.issubset(metric_set):
        family = "resource_saturation"
    elif "cpu_usage" in metric_set or "load_1m" in metric_set:
        family = "cpu_load_pressure"
    elif "memory_usage" in metric_set:
        family = "memory_pressure"
    elif "disk_usage" in metric_set:
        family = "disk_storage_pressure"

    raw = f"{hostname}::{family}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def build_incident_title(affected_metrics: List[str], severity: str) -> str:
    """Generate a clean, professional incident title."""
    metric_labels = {
        "cpu_usage": "CPU",
        "memory_usage": "Memory",
        "disk_usage": "Disk",
        "load_1m": "System Load",
        "response_time_ms": "Response Time",
    }
    readable = [metric_labels.get(m, m.replace("_", " ").title()) for m in affected_metrics]

    if not readable:
        return f"{severity}: System Anomaly Detected"
    if len(readable) == 1:
        return f"{severity}: EC2 {readable[0]} Anomaly Detected"
    if len(readable) == 2:
        return f"{severity}: EC2 {readable[0]} and {readable[1]} Pressure"

    primary = ", ".join(readable[:-1])
    return f"{severity}: EC2 {primary} and {readable[-1]} Resource Saturation"


def generate_rule_based_cause(
    anomalies: List[Anomaly], processes: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Deterministic probable-cause explanation using observed evidence.
    Distinguishes observed facts from inference. Uses 'Likely' and 'Evidence suggests'.
    """
    metrics = {a.metric_name for a in anomalies}

    proc_detail = ""
    if processes:
        top = processes[0]
        p_name = top.get("name") or top.get("process_name")
        p_cpu = top.get("cpu_percent")
        p_mem = top.get("memory_percent")
        if p_name and (p_cpu or p_mem):
            proc_detail = f" Top active process is '{p_name}' consuming {p_cpu or 0}% CPU and {p_mem or 0}% memory."

    if len(metrics) >= 4:
        return (
            "Probable cause: Comprehensive resource saturation affecting CPU, memory, "
            "system load, and storage/network simultaneously. Evidence suggests the instance "
            f"is experiencing heavy multi-tenant or multi-service workload exhaustion.{proc_detail}"
        )

    if "cpu_usage" in metrics and "memory_usage" in metrics and "load_1m" in metrics:
        return (
            "Probable cause: Simultaneous CPU, memory, and system load pressure indicates "
            f"severe system or application resource saturation.{proc_detail}"
        )

    if "cpu_usage" in metrics and "response_time_ms" in metrics:
        return (
            "Probable cause: CPU saturation coinciding with degraded application response time "
            f"suggests request queueing or thread starvation.{proc_detail}"
        )

    if "cpu_usage" in metrics and "load_1m" in metrics:
        return (
            "Probable cause: Elevated CPU utilization and system load average exceeding core capacity. "
            f"Evidence suggests an intensive compute job or runaway process.{proc_detail}"
        )

    if "memory_usage" in metrics:
        return (
            "Probable cause: Memory exhaustion with available memory critically constrained. "
            f"Likely related to high buffer allocation or a memory-intensive process.{proc_detail}"
        )

    if "disk_usage" in metrics:
        return (
            "Probable cause: Root filesystem storage capacity nearing critical threshold. "
            "Likely caused by unrotated logs or rapid temporary file creation."
        )

    affected = ", ".join(sorted(metrics))
    return f"Probable cause: Anomalous behavior observed in {affected}. Review system activity."


def generate_rule_based_recommendation(anomalies: List[Anomaly]) -> str:
    """Deterministic actionable recommendations."""
    metrics = {a.metric_name for a in anomalies}
    actions: List[str] = []

    if "cpu_usage" in metrics or "load_1m" in metrics:
        actions.append("Inspect top CPU-consuming processes using `ps -eo pid,comm,%cpu --sort=-%cpu | head -n 10`")
    if "memory_usage" in metrics:
        actions.append("Review per-process memory consumption and system cache using `free -m` and `ps -eo pid,comm,%mem --sort=-%mem | head -n 10`")
    if "disk_usage" in metrics:
        actions.append("Inspect large files and directory usage with `df -h` and `du -sh /var/log/*`")
    if "response_time_ms" in metrics:
        actions.append("Check web application connection pools, worker thread counts, and upstream service latency")

    actions.append("Examine system journal for kernel warnings via `journalctl -p warning..err -n 50 --no-pager`")
    actions.append("Evaluate EC2 instance sizing and consider upgrading compute/memory specs if workload is legitimate")

    return " ".join(f"({i+1}) {act}." for i, act in enumerate(actions))


def generate_rule_based_summary(
    anomalies: List[Anomaly], severity: str, hostname: str
) -> str:
    """Deterministic incident summary."""
    metrics = sorted(list({a.metric_name for a in anomalies}))
    count = len(anomalies)
    return (
        f"Incident on host '{hostname}' with {severity} severity. "
        f"Detected {count} abnormal condition(s) across: {', '.join(metrics)}. "
        "Deterministic analysis engine correlated these events as a single incident."
    )
