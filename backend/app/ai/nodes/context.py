"""
Node 1: Collect Incident Context.
Gathers and normalizes raw incident data, metrics, anomalies, and evidence.
"""

from __future__ import annotations

from typing import Any, Dict
from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger

logger = get_logger(__name__)


def collect_incident_context(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Ensure all context lists and dictionaries are properly initialized and present.
    """
    hostname = state.get("hostname") or state.get("host") or "unknown"
    incident_id = state.get("incident_id") or "unknown"

    metrics = state.get("recent_metrics", [])
    anomalies = state.get("anomalies", [])
    process_evidence = state.get("process_evidence", [])
    log_evidence = state.get("log_evidence", [])

    logger.debug(
        "langgraph_collect_context",
        incident_id=incident_id,
        host=hostname,
        anomalies_count=len(anomalies),
        metrics_count=len(metrics),
    )

    return {
        "host": hostname,
        "hostname": hostname,
        "incident_id": incident_id,
        "recent_metrics": metrics,
        "anomalies": anomalies,
        "process_evidence": process_evidence,
        "log_evidence": log_evidence,
        "errors": state.get("errors", []),
    }
