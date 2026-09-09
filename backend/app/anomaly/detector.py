"""
Anomaly detector orchestrator.
Applies deterministic threshold and trend rules across all collected metrics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional
from app.anomaly.rules import DetectedAnomaly, evaluate_threshold
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.anomaly import Anomaly

logger = get_logger(__name__)


def detect_anomalies(
    hostname: str,
    cpu_usage: Optional[float] = None,
    cpu_count: Optional[int] = None,
    memory_usage: Optional[float] = None,
    disk_usage: Optional[float] = None,
    load_1m: Optional[float] = None,
    response_time_ms: Optional[float] = None,
) -> List[DetectedAnomaly]:
    """
    Run deterministic threshold checks against measured metrics.

    Preserves None: unmeasured metrics are skipped without assuming normal.
    """
    settings = get_settings()
    results: List[DetectedAnomaly] = []

    # 1. CPU
    cpu_anom = evaluate_threshold(
        hostname=hostname,
        metric_name="cpu_usage",
        value=cpu_usage,
        warning_threshold=settings.cpu_warning_threshold,
        critical_threshold=settings.cpu_critical_threshold,
        label="CPU usage",
    )
    if cpu_anom:
        results.append(cpu_anom)

    # 2. Memory
    mem_anom = evaluate_threshold(
        hostname=hostname,
        metric_name="memory_usage",
        value=memory_usage,
        warning_threshold=settings.memory_warning_threshold,
        critical_threshold=settings.memory_critical_threshold,
        label="Memory usage",
    )
    if mem_anom:
        results.append(mem_anom)

    # 3. Disk
    disk_anom = evaluate_threshold(
        hostname=hostname,
        metric_name="disk_usage",
        value=disk_usage,
        warning_threshold=settings.disk_warning_threshold,
        critical_threshold=settings.disk_critical_threshold,
        label="Disk usage",
    )
    if disk_anom:
        results.append(disk_anom)

    # 4. System Load (relative to CPU core count)
    if load_1m is not None:
        cores = cpu_count or 1
        load_warn = float(cores)
        load_crit = float(cores * 2)
        load_anom = evaluate_threshold(
            hostname=hostname,
            metric_name="load_1m",
            value=load_1m,
            warning_threshold=load_warn,
            critical_threshold=load_crit,
            label="System load (1m)",
            unit="",
        )
        if load_anom:
            results.append(load_anom)

    # 5. Response Time (optional probe)
    if response_time_ms is not None:
        rt_anom = evaluate_threshold(
            hostname=hostname,
            metric_name="response_time_ms",
            value=response_time_ms,
            warning_threshold=settings.response_time_warning_ms,
            critical_threshold=settings.response_time_critical_ms,
            label="HTTP response time",
            unit="ms",
        )
        if rt_anom:
            results.append(rt_anom)

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
    """Convert a DetectedAnomaly into a SQLAlchemy Anomaly model instance."""
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
