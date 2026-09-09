"""
Anomaly detection rules and threshold evaluation.

Deterministic Python rules:
- Strictly ignores None values (uncollected/failed metrics are NOT classified as normal).
- Supports warning and critical thresholds.
- Applies persistence tracking.
- Implements explainable trend detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from app.anomaly.persistence import record_violation, reset_persistence
from app.core.config import get_settings


@dataclass
class DetectedAnomaly:
    """Represents an anomaly detected in a metric snapshot."""

    metric_name: str
    observed_value: float
    threshold: float
    anomaly_type: str
    severity: str
    description: str
    is_persistent: bool = False
    consecutive_count: int = 1


def evaluate_threshold(
    hostname: str,
    metric_name: str,
    value: Optional[float],
    warning_threshold: float,
    critical_threshold: float,
    label: str,
    unit: str = "%",
) -> Optional[DetectedAnomaly]:
    """
    Evaluate a metric against warning and critical thresholds.

    CRITICAL RULE:
    If value is None, the metric was not collected or failed.
    Return None (not evaluated). Do NOT classify as normal.
    """
    if value is None:
        return None

    settings = get_settings()

    if value >= critical_threshold:
        severity = "CRITICAL"
        threshold = critical_threshold
    elif value >= warning_threshold:
        severity = "WARNING"
        threshold = warning_threshold
    else:
        # Value was measured and is genuinely normal -> reset persistence
        reset_persistence(hostname, metric_name)
        return None

    count, is_persistent = record_violation(
        hostname=hostname,
        metric_name=metric_name,
        required_samples=settings.anomaly_consecutive_samples,
    )

    anomaly_type = "persistent_high" if is_persistent else "threshold_exceeded"
    persistence_note = (
        f" (persisted across {count} consecutive observations)"
        if is_persistent
        else f" (observation {count}/{settings.anomaly_consecutive_samples} before persistence threshold)"
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


def detect_trend(values: List[float], min_samples: int = 3) -> Optional[str]:
    """
    Detect explainable deteriorating or improving trends from recent values.
    Returns 'deteriorating', 'improving', or None.
    """
    clean_vals = [v for v in values if v is not None]
    if len(clean_vals) < min_samples:
        return None

    # Check if strictly increasing
    is_increasing = all(clean_vals[i] < clean_vals[i + 1] for i in range(len(clean_vals) - 1))
    if is_increasing:
        diff = clean_vals[-1] - clean_vals[0]
        if diff >= 10.0:
            return "deteriorating"

    # Check if strictly decreasing
    is_decreasing = all(clean_vals[i] > clean_vals[i + 1] for i in range(len(clean_vals) - 1))
    if is_decreasing:
        diff = clean_vals[0] - clean_vals[-1]
        if diff >= 10.0:
            return "improving"

    return None
