"""Node 3: Assess incident severity from evidence."""

from __future__ import annotations

from typing import Any

from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger

logger = get_logger(__name__)


def determine_severity_node(state: IncidentAnalysisState) -> dict[str, Any]:
    """
    Determine the overall severity from anomaly evidence.

    Rules (deterministic, no LLM):
    - Any CRITICAL anomaly → CRITICAL
    - Correlation score > 6 → CRITICAL
    - 3+ affected metrics → CRITICAL
    - Otherwise → WARNING
    """
    anomalies = state.get("anomalies", [])
    affected_metrics = state.get("affected_metrics", [])
    correlation_score = state.get("correlation_score", 0.0)
    incident_data = state.get("incident_data", {})

    severity_votes = [a.get("severity", "WARNING") for a in anomalies]

    if "CRITICAL" in severity_votes:
        severity = "CRITICAL"
        reason = "at least one CRITICAL threshold anomaly detected"
    elif correlation_score >= 6.0:
        severity = "CRITICAL"
        reason = f"high correlation score ({correlation_score:.1f})"
    elif len(affected_metrics) >= 3:
        severity = "CRITICAL"
        reason = f"{len(affected_metrics)} metrics simultaneously affected"
    else:
        severity = "WARNING"
        reason = "no critical threshold breaches or wide-scope impact"

    logger.info(
        "severity_determined",
        incident_id=state.get("incident_id"),
        severity=severity,
        reason=reason,
    )

    return {"assessed_severity": severity}
