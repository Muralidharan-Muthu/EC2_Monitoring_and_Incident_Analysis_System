"""Node 6: Generate the final human-readable analysis summary."""

from __future__ import annotations

from typing import Any

from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_summary_node(state: IncidentAnalysisState) -> dict[str, Any]:
    """
    Compose the final reasoning summary and ensure all outputs are present.

    If the LLM produced a reasoning_summary, it is kept.
    Otherwise a deterministic summary is generated from the state.
    """
    existing_summary = state.get("reasoning_summary", "").strip()
    if existing_summary:
        logger.debug("summary_from_llm")
        # Ensure confidence is set
        return {"confidence": state.get("confidence", 0.7)}

    # Generate deterministic summary
    affected = state.get("affected_metrics", [])
    severity = state.get("assessed_severity", "WARNING")
    evidence = state.get("evidence", [])
    observation_count = state.get("incident_data", {}).get("observation_count", 1)
    correlation_score = state.get("correlation_score", 0.0)
    time_span = state.get("time_span_minutes", 0.0)

    metric_labels = {
        "cpu_usage": "CPU",
        "memory_usage": "Memory",
        "disk_usage": "Disk",
        "load_1m": "System Load",
        "response_time_ms": "Response Time",
    }
    readable_metrics = [metric_labels.get(m, m) for m in affected]

    if len(readable_metrics) > 1:
        metrics_str = ", ".join(readable_metrics[:-1]) + f" and {readable_metrics[-1]}"
    else:
        metrics_str = readable_metrics[0] if readable_metrics else "unknown metrics"

    summary_parts = [
        f"A {severity} incident was detected involving {metrics_str}.",
    ]

    if observation_count > 1:
        summary_parts.append(
            f"The condition persisted across {observation_count} consecutive "
            f"monitoring observations."
        )

    if time_span > 0:
        summary_parts.append(
            f"The anomalous period spans approximately {time_span:.1f} minutes."
        )

    if correlation_score >= 6.0:
        summary_parts.append(
            "The high correlation score indicates these anomalies are strongly "
            "related and should be treated as a single compound incident."
        )
    elif correlation_score >= 3.0:
        summary_parts.append(
            "The anomalies show moderate correlation, suggesting a common underlying cause."
        )

    if evidence:
        summary_parts.append(f"Key evidence: {evidence[0]}.")

    summary = " ".join(summary_parts)

    # Confidence is lower for rule-based (no LLM)
    confidence = min(0.5 + (correlation_score * 0.05), 0.75)

    logger.info(
        "summary_generated",
        incident_id=state.get("incident_id"),
        source="rule_based",
        length=len(summary),
    )

    return {
        "reasoning_summary": summary,
        "confidence": round(confidence, 2),
    }
