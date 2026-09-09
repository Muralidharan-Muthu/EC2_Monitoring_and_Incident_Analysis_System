"""Node 1: Collect and validate incident context from the database."""

from __future__ import annotations

from typing import Any

from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger

logger = get_logger(__name__)


def collect_context_node(state: IncidentAnalysisState) -> dict[str, Any]:
    """
    Validate that required context data is present before analysis begins.

    This node acts as a guard: if critical data is missing, it marks the
    state as invalid so downstream nodes can apply rule-based fallback.
    """
    notes = []
    valid = True

    if not state.get("incident_data"):
        notes.append("Incident data not found")
        valid = False

    anomalies = state.get("anomalies", [])
    if not anomalies:
        notes.append("No anomalies associated with this incident")
        valid = False

    recent_metrics = state.get("recent_metrics", [])
    if not recent_metrics:
        notes.append("No recent metric data available for trend analysis")
        # Not fatal — we can still analyze with anomaly data alone

    if not valid:
        logger.warning(
            "context_validation_failed",
            incident_id=state.get("incident_id"),
            notes=notes,
        )
    else:
        logger.info(
            "context_collected",
            incident_id=state.get("incident_id"),
            anomaly_count=len(anomalies),
            metric_count=len(recent_metrics),
        )

    return {"valid": valid, "validation_notes": notes}
