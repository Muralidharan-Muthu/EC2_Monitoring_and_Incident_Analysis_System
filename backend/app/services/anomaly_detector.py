"""
Rule-based anomaly detector.

Implements deterministic threshold-based detection with persistence tracking.
The LLM is NOT involved in this stage — all detection is explicit Python logic
with configurable thresholds.

Design principles:
  - Thresholds come from configuration, not hard-coded constants.
  - Persistence: N consecutive threshold violations → "persistent" anomaly.
  - Each metric is evaluated independently.
  - Severity: WARNING | CRITICAL.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.anomaly import Anomaly
from app.schemas.metric import MetricIngest

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Persistence state — in-memory tracking of consecutive threshold violations.
# Key: (hostname, metric_name)  Value: consecutive violation count
# ---------------------------------------------------------------------------
_consecutive_counts: dict[tuple[str, str], int] = defaultdict(int)


@dataclass
class DetectedAnomaly:
    """Intermediate anomaly result before database persistence."""

    metric_name: str
    observed_value: float
    threshold: float
    anomaly_type: str
    severity: str
    description: str
    is_persistent: bool = False
    consecutive_count: int = 1


def reset_persistence_state(hostname: str, metric_name: str) -> None:
    """Reset consecutive count for a metric when it returns to normal."""
    key = (hostname, metric_name)
    _consecutive_counts.pop(key, None)


def _check_threshold(
    hostname: str,
    metric_name: str,
    value: float,
    warning_threshold: float,
    critical_threshold: float,
    label: str,
    unit: str = "%",
) -> Optional[DetectedAnomaly]:
    """
    Check a single metric value against warning/critical thresholds.

    Tracks consecutive violations for persistence detection.
    """
    settings = get_settings()
    key = (hostname, metric_name)

    if value >= critical_threshold:
        severity = "CRITICAL"
        threshold = critical_threshold
    elif value >= warning_threshold:
        severity = "WARNING"
        threshold = warning_threshold
    else:
        # Value is normal — reset consecutive counter
        _consecutive_counts.pop(key, None)
        return None

    # Increment consecutive violation count
    _consecutive_counts[key] += 1
    count = _consecutive_counts[key]
    required = settings.anomaly_consecutive_samples

    is_persistent = count >= required
    anomaly_type = "persistent_high" if is_persistent else "threshold_exceeded"

    persistence_note = (
        f" (persisted across {count} consecutive observations)"
        if is_persistent
        else f" (observation {count}/{required} before persistence threshold)"
    )

    description = (
        f"{label} is {value:.1f}{unit}, exceeding {severity.lower()} "
        f"threshold of {threshold:.1f}{unit}.{persistence_note}"
    )

    return DetectedAnomaly(
        metric_name=metric_name,
        observed_value=value,
        threshold=threshold,
        anomaly_type=anomaly_type,
        severity=severity,
        description=description,
        is_persistent=is_persistent,
        consecutive_count=count,
    )


def detect_anomalies(metric: MetricIngest) -> list[DetectedAnomaly]:
    """
    Run all configured anomaly checks against a metric payload.

    Returns a list of DetectedAnomaly objects.
    An empty list means the system is operating normally.

    This function is deterministic and has no external dependencies.
    """
    settings = get_settings()
    results: list[DetectedAnomaly] = []
    hostname = metric.hostname

    # ---- CPU ----
    cpu_anomaly = _check_threshold(
        hostname=hostname,
        metric_name="cpu_usage",
        value=metric.cpu_usage,
        warning_threshold=settings.cpu_warning_threshold,
        critical_threshold=settings.cpu_critical_threshold,
        label="CPU usage",
    )
    if cpu_anomaly:
        results.append(cpu_anomaly)

    # ---- Memory ----
    mem_anomaly = _check_threshold(
        hostname=hostname,
        metric_name="memory_usage",
        value=metric.memory_usage,
        warning_threshold=settings.memory_warning_threshold,
        critical_threshold=settings.memory_critical_threshold,
        label="Memory usage",
    )
    if mem_anomaly:
        results.append(mem_anomaly)

    # ---- Disk ----
    disk_anomaly = _check_threshold(
        hostname=hostname,
        metric_name="disk_usage",
        value=metric.disk_usage,
        warning_threshold=settings.disk_warning_threshold,
        critical_threshold=settings.disk_critical_threshold,
        label="Disk usage",
    )
    if disk_anomaly:
        results.append(disk_anomaly)

    # ---- System Load (relative to CPU count) ----
    cpu_count = max(metric.cpu_count, 1)
    load_warning = float(cpu_count)       # Load > n_cores = WARNING
    load_critical = float(cpu_count * 2)  # Load > 2×n_cores = CRITICAL

    load_anomaly = _check_threshold(
        hostname=hostname,
        metric_name="load_1m",
        value=metric.load_1m,
        warning_threshold=load_warning,
        critical_threshold=load_critical,
        label="System load (1m)",
        unit="",
    )
    if load_anomaly:
        results.append(load_anomaly)

    # ---- Response Time (optional — only if measured) ----
    if metric.response_time_ms is not None:
        rt_warning = 2000.0   # >2s warning
        rt_critical = 5000.0  # >5s critical
        rt_anomaly = _check_threshold(
            hostname=hostname,
            metric_name="response_time_ms",
            value=metric.response_time_ms,
            warning_threshold=rt_warning,
            critical_threshold=rt_critical,
            label="HTTP response time",
            unit="ms",
        )
        if rt_anomaly:
            results.append(rt_anomaly)

    if results:
        logger.info(
            "anomalies_detected",
            hostname=hostname,
            count=len(results),
            metrics=[a.metric_name for a in results],
            severities=[a.severity for a in results],
        )
    else:
        logger.debug("no_anomalies", hostname=hostname)

    return results


def build_anomaly_model(
    detected: DetectedAnomaly, metric_id: uuid.UUID, timestamp: datetime
) -> Anomaly:
    """Convert a DetectedAnomaly into a database Anomaly model instance."""
    return Anomaly(
        metric_id=metric_id,
        metric_name=detected.metric_name,
        observed_value=detected.observed_value,
        threshold=detected.threshold,
        anomaly_type=detected.anomaly_type,
        severity=detected.severity,
        description=detected.description,
        is_persistent=detected.is_persistent,
        consecutive_count=detected.consecutive_count,
        detected_at=timestamp,
    )
