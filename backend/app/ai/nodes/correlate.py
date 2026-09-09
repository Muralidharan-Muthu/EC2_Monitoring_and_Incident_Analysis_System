"""Node 2: Correlate anomalies and extract evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger

logger = get_logger(__name__)


def correlate_node(state: IncidentAnalysisState) -> dict[str, Any]:
    """
    Analyse the temporal relationship between anomalies and build evidence list.

    This node operates deterministically — no LLM calls.
    """
    anomalies = state.get("anomalies", [])
    recent_metrics = state.get("recent_metrics", [])

    # Extract unique affected metrics
    affected_metrics = list({a.get("metric_name", "") for a in anomalies})

    # Build evidence statements
    evidence: list[str] = []

    # Metric-specific evidence
    for anomaly in anomalies:
        metric = anomaly.get("metric_name", "unknown")
        value = anomaly.get("observed_value", 0)
        threshold = anomaly.get("threshold", 0)
        severity = anomaly.get("severity", "UNKNOWN")
        is_persistent = anomaly.get("is_persistent", False)
        count = anomaly.get("consecutive_count", 1)

        evidence_item = (
            f"{metric.replace('_', ' ').title()} reached {value:.1f} "
            f"(threshold: {threshold:.1f}) — {severity}"
        )
        if is_persistent:
            evidence_item += f" — persisted across {count} consecutive observations"
        evidence.append(evidence_item)

    # Trend evidence from metric history
    if len(recent_metrics) >= 2:
        first = recent_metrics[0]
        last = recent_metrics[-1]
        cpu_trend = last.get("cpu_usage", 0) - first.get("cpu_usage", 0)
        mem_trend = last.get("memory_usage", 0) - first.get("memory_usage", 0)

        if abs(cpu_trend) > 5:
            direction = "increased" if cpu_trend > 0 else "decreased"
            evidence.append(
                f"CPU usage {direction} by {abs(cpu_trend):.1f}% "
                f"over the observation period"
            )
        if abs(mem_trend) > 5:
            direction = "increased" if mem_trend > 0 else "decreased"
            evidence.append(
                f"Memory usage {direction} by {abs(mem_trend):.1f}% "
                f"over the observation period"
            )

    # Process evidence
    process_snapshots = state.get("process_snapshots", [])
    for proc in process_snapshots[:2]:
        ptype = proc.get("snapshot_type", "")
        name = proc.get("process_name", "unknown")
        cpu_pct = proc.get("cpu_percent")
        mem_pct = proc.get("memory_percent")

        if ptype == "top_cpu" and cpu_pct is not None:
            evidence.append(f"Top CPU process: {name} consuming {cpu_pct:.1f}% CPU")
        elif ptype == "top_memory" and mem_pct is not None:
            evidence.append(f"Top memory process: {name} consuming {mem_pct:.1f}% memory")

    # Compute time span
    timestamps = [
        m.get("timestamp") for m in recent_metrics if m.get("timestamp")
    ]
    time_span = 0.0
    if len(timestamps) >= 2:
        try:
            t1 = datetime.fromisoformat(str(timestamps[0]).replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(str(timestamps[-1]).replace("Z", "+00:00"))
            time_span = abs((t2 - t1).total_seconds() / 60.0)
        except (ValueError, TypeError):
            time_span = 0.0

    correlation_score = state.get("correlation_score", 0.0)

    logger.info(
        "correlation_complete",
        incident_id=state.get("incident_id"),
        affected_metrics=affected_metrics,
        evidence_count=len(evidence),
        time_span_minutes=time_span,
    )

    return {
        "affected_metrics": affected_metrics,
        "evidence": evidence,
        "time_span_minutes": time_span,
    }
