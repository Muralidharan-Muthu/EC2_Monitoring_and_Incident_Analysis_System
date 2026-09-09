"""Node 5: Generate recommended actions (rule-based if LLM already populated)."""

from __future__ import annotations

from typing import Any

from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger
from app.services.correlation_engine import generate_rule_based_recommendation

logger = get_logger(__name__)


def recommend_action_node(state: IncidentAnalysisState) -> dict[str, Any]:
    """
    Ensure recommended_actions is populated.

    If the LLM already provided recommendations (in determine_cause_node),
    this node is a no-op. Otherwise it generates rule-based recommendations.
    """
    existing_actions = state.get("recommended_actions")
    if existing_actions:
        logger.debug("recommendations_from_llm", count=len(existing_actions))
        return {}  # No changes needed

    anomalies = state.get("anomalies", [])

    class _MockAnomaly:
        def __init__(self, d: dict) -> None:
            self.metric_name = d.get("metric_name", "")

    mock_anomalies = [_MockAnomaly(a) for a in anomalies]
    recommendation_text = generate_rule_based_recommendation(mock_anomalies)  # type: ignore[arg-type]

    # Split by numbered items into list
    import re
    parts = re.split(r"\(\d+\)\s+", recommendation_text)
    actions = [p.strip().rstrip(".") for p in parts if p.strip()]

    logger.info(
        "recommendations_generated",
        incident_id=state.get("incident_id"),
        count=len(actions),
        source="rule_based",
    )

    return {"recommended_actions": actions}
