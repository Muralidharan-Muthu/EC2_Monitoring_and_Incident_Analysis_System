"""
Deterministic incident severity logic.

Severity tiers:
- LOW: single warning anomaly
- MEDIUM: multiple warning anomalies
- HIGH: persistent critical anomaly or multiple critical anomalies
- CRITICAL: multi-metric resource saturation (e.g. CPU + Memory + Load, or 4+ anomalies)
"""

from __future__ import annotations

from typing import List
from app.models.anomaly import Anomaly


def determine_severity(anomalies: List[Anomaly]) -> str:
    """
    Evaluate deterministic severity from the set of correlated anomalies.
    """
    if not anomalies:
        return "LOW"

    metrics = {a.metric_name for a in anomalies}
    critical_count = sum(1 for a in anomalies if a.severity == "CRITICAL")
    warning_count = sum(1 for a in anomalies if a.severity == "WARNING")
    has_persistent = any(a.is_persistent for a in anomalies)

    # 1. CRITICAL Tier:
    # Full multi-metric resource saturation:
    # CPU + Memory + Load, or CPU + Memory + Response Time, or 4+ simultaneous abnormal metrics
    if len(metrics) >= 4:
        return "CRITICAL"

    if (
        "cpu_usage" in metrics
        and "memory_usage" in metrics
        and ("load_1m" in metrics or "response_time_ms" in metrics)
    ):
        return "CRITICAL"

    if critical_count >= 2 and ("cpu_usage" in metrics or "memory_usage" in metrics):
        return "CRITICAL"

    # 2. HIGH Tier:
    # Any persistent critical anomaly or multiple criticals
    if critical_count > 0:
        if has_persistent or critical_count >= 2:
            return "HIGH"
        return "HIGH"

    # 3. MEDIUM Tier:
    # Multiple warning anomalies
    if warning_count > 1:
        return "MEDIUM"

    # 4. LOW Tier:
    # Single warning anomaly
    return "LOW"
