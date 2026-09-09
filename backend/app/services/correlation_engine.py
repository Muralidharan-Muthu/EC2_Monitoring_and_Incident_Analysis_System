"""
Correlation Engine — groups related anomalies into a single incident.

Design principles:
  - Temporal proximity: anomalies within CORRELATION_WINDOW_MINUTES are candidates.
  - Scoring: each type of anomaly contributes a weight to the correlation score.
  - The engine avoids creating duplicate incidents for the same ongoing condition.
  - All logic is deterministic Python — no LLM involvement.

Correlation score weights:
  cpu_usage:          +2
  memory_usage:       +2
  load_1m:            +2
  disk_usage:         +1
  response_time_ms:   +2
  persistent anomaly: +1 bonus per persistent anomaly
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.anomaly import Anomaly

logger = get_logger(__name__)

# Correlation score weights per metric
METRIC_WEIGHTS: dict[str, float] = {
    "cpu_usage": 2.0,
    "memory_usage": 2.0,
    "load_1m": 2.0,
    "disk_usage": 1.0,
    "response_time_ms": 2.0,
}

PERSISTENCE_BONUS = 1.0  # Extra weight for persistent anomalies


def compute_correlation_score(anomalies: list[Anomaly]) -> float:
    """
    Compute a correlation score for a set of anomalies.

    Higher score = more severe and diverse resource pressure.
    Score is used to determine incident severity and in the LLM context.
    """
    score = 0.0
    for anomaly in anomalies:
        weight = METRIC_WEIGHTS.get(anomaly.metric_name, 0.5)
        score += weight
        if anomaly.is_persistent:
            score += PERSISTENCE_BONUS
    return round(score, 2)


def compute_incident_key(hostname: str, affected_metrics: list[str]) -> str:
    """
    Compute a deterministic deduplication key for an incident.

    Key is derived from: hostname + sorted metric names.
    This ensures the same set of failing metrics always maps to the same key,
    preventing duplicate incidents for the same ongoing condition.
    """
    sorted_metrics = sorted(set(affected_metrics))
    raw = f"{hostname}::{':'.join(sorted_metrics)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def determine_severity(anomalies: list[Anomaly]) -> str:
    """
    Determine overall incident severity from the worst constituent anomaly.

    Rules:
    - Any CRITICAL anomaly → incident is CRITICAL
    - All WARNING → incident is WARNING
    """
    severities = {a.severity for a in anomalies}
    if "CRITICAL" in severities:
        return "CRITICAL"
    return "WARNING"


def build_incident_title(affected_metrics: list[str], severity: str) -> str:
    """Generate a human-readable incident title."""
    metric_labels = {
        "cpu_usage": "CPU",
        "memory_usage": "Memory",
        "disk_usage": "Disk",
        "load_1m": "System Load",
        "response_time_ms": "Response Time",
    }
    readable = [metric_labels.get(m, m.replace("_", " ").title()) for m in affected_metrics]

    if len(readable) == 1:
        return f"{severity}: {readable[0]} Anomaly Detected"
    elif len(readable) == 2:
        return f"{severity}: {readable[0]} and {readable[1]} Pressure Detected"
    else:
        primary = ", ".join(readable[:-1])
        return f"{severity}: {primary} and {readable[-1]} Resource Saturation"


def generate_rule_based_cause(anomalies: list[Anomaly]) -> str:
    """
    Generate a deterministic probable-cause statement from anomaly evidence.

    Uses explicit rule patterns to avoid speculation.
    Checks are ordered from most specific (many metrics) to least specific.
    """
    metrics = {a.metric_name for a in anomalies}

    # Pattern: Full saturation (4+ metrics simultaneously) — check first
    if len(metrics) >= 4:
        return (
            "Probable cause: Comprehensive resource saturation affecting CPU, memory, "
            "disk, and system load simultaneously. The instance may be significantly "
            "undersized for the current workload, or an abnormal process is consuming "
            "all available resources."
        )

    # Pattern: CPU + Memory + Load → resource saturation
    if "cpu_usage" in metrics and "memory_usage" in metrics and "load_1m" in metrics:
        return (
            "Probable cause: Simultaneous CPU, memory, and load pressure indicates "
            "system or application resource saturation. Evidence suggests an "
            "intensive workload or a resource-leaking process."
        )

    # Pattern: CPU + Memory + response time → application overload
    if "cpu_usage" in metrics and "memory_usage" in metrics and "response_time_ms" in metrics:
        return (
            "Probable cause: CPU and memory saturation coinciding with increased response "
            "time suggests application-level resource overload. The application may be "
            "resource-constrained or experiencing a traffic surge."
        )

    # Pattern: CPU + Load (+ persistent) → process saturation
    if "cpu_usage" in metrics and "load_1m" in metrics:
        persistent = [a for a in anomalies if a.is_persistent]
        if persistent:
            return (
                "Probable cause: Sustained CPU and system load saturation detected "
                "across multiple consecutive observations. This pattern suggests a "
                "high-resource process or increased application workload is exhausting "
                "available CPU capacity."
            )
        return (
            "Probable cause: Elevated CPU usage and system load detected simultaneously. "
            "A process or workload spike is a likely contributing factor."
        )

    # Pattern: Memory only
    if "memory_usage" in metrics and "cpu_usage" not in metrics:
        return (
            "Probable cause: High memory usage with available memory critically low. "
            "A memory-intensive process or memory leak is a likely contributing factor."
        )

    # Pattern: Disk only
    if "disk_usage" in metrics and len(metrics) == 1:
        return (
            "Probable cause: Disk usage approaching capacity. Log accumulation, "
            "large file creation, or insufficient cleanup processes are likely "
            "contributing factors."
        )

    # Generic fallback
    affected = ", ".join(sorted(metrics))
    return (
        f"Probable cause: Abnormal values detected for {affected}. "
        "Review system processes and application logs to identify the root cause."
    )


def generate_rule_based_recommendation(anomalies: list[Anomaly]) -> str:
    """Generate actionable recommendations based on anomaly patterns."""
    metrics = {a.metric_name for a in anomalies}
    actions = []

    if "cpu_usage" in metrics:
        actions.append("Identify and inspect the top CPU-consuming processes (ps aux, top)")
    if "memory_usage" in metrics:
        actions.append("Check memory usage per process and look for memory leaks (free -m, ps aux --sort=-%mem)")
    if "disk_usage" in metrics:
        actions.append("Identify large files or directories consuming disk space (df -h, du -sh /*)")
    if "load_1m" in metrics:
        actions.append("Review process queue length and wait states (uptime, vmstat)")
    if "response_time_ms" in metrics:
        actions.append("Investigate application response degradation and check application logs")

    # Universal recommendations
    actions.append("Review relevant system logs (journalctl -xe, /var/log/syslog)")
    actions.append("Evaluate whether the current instance type is appropriately sized for the workload")

    return " ".join(f"({i+1}) {a}." for i, a in enumerate(actions))
