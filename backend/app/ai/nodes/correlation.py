"""
Node 3: Correlate Related Events.
Analyzes temporal and semantic relationships across observed anomalies.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.ai.state import IncidentAnalysisState

METRIC_WEIGHTS: dict[str, float] = {
    "cpu_usage": 2.5,
    "memory_usage": 2.5,
    "load_1m": 2.0,
    "disk_usage": 1.5,
    "response_time_ms": 2.0,
}


def correlate_events(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Compute multi-metric correlation score and identify affected subsystems.
    """
    anomalies = state.get("anomalies", [])
    affected_metrics: List[str] = sorted(list({a.get("metric_name") for a in anomalies if a.get("metric_name")}))

    score = 0.0
    for a in anomalies:
        m_name = a.get("metric_name", "")
        weight = METRIC_WEIGHTS.get(m_name, 1.0)
        score += weight
        if a.get("is_persistent"):
            score += 1.0

    return {
        "affected_metrics": affected_metrics,
        "correlation_score": round(score, 2),
        "time_span_minutes": 5.0,
    }
