"""
LangGraph workflow for incident analysis.

Graph structure:
  START → collect_context → correlate → determine_severity
        → determine_cause → recommend_action → generate_summary → END

Each node has a single responsibility. The graph uses the typed
IncidentAnalysisState to pass data between nodes.
"""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.ai.state import IncidentAnalysisState
from app.ai.nodes.collect_context import collect_context_node
from app.ai.nodes.correlate import correlate_node
from app.ai.nodes.determine_severity import determine_severity_node
from app.ai.nodes.determine_cause import determine_cause_node
from app.ai.nodes.recommend_action import recommend_action_node
from app.ai.nodes.generate_summary import generate_summary_node
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_analysis_graph() -> StateGraph:
    """
    Assemble and compile the incident analysis LangGraph.

    Returns a compiled graph ready for invocation.
    """
    graph = StateGraph(IncidentAnalysisState)

    # Register nodes
    graph.add_node("collect_context", collect_context_node)
    graph.add_node("correlate", correlate_node)
    graph.add_node("determine_severity", determine_severity_node)
    graph.add_node("determine_cause", determine_cause_node)
    graph.add_node("recommend_action", recommend_action_node)
    graph.add_node("generate_summary", generate_summary_node)

    # Define edges (sequential flow)
    graph.add_edge(START, "collect_context")
    graph.add_edge("collect_context", "correlate")
    graph.add_edge("correlate", "determine_severity")
    graph.add_edge("determine_severity", "determine_cause")
    graph.add_edge("determine_cause", "recommend_action")
    graph.add_edge("recommend_action", "generate_summary")
    graph.add_edge("generate_summary", END)

    return graph.compile()


# Module-level compiled graph (created once)
_compiled_graph = None


def get_analysis_graph():
    """Return the compiled analysis graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_analysis_graph()
    return _compiled_graph


async def run_incident_analysis(
    incident_id: str,
    hostname: str,
    incident_data: dict[str, Any],
    recent_metrics: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    process_snapshots: list[dict[str, Any]],
    correlation_score: float,
) -> IncidentAnalysisState:
    """
    Run the full incident analysis workflow for a given incident.

    Args:
        incident_id: UUID string of the incident.
        hostname: EC2 hostname.
        incident_data: Serialized incident record.
        recent_metrics: List of recent metric dicts (last N observations).
        anomalies: List of anomaly dicts associated with this incident.
        process_snapshots: List of process snapshot dicts.
        correlation_score: Pre-computed correlation score.

    Returns:
        The final IncidentAnalysisState after all nodes have executed.
    """
    graph = get_analysis_graph()

    initial_state: IncidentAnalysisState = {
        "incident_id": incident_id,
        "hostname": hostname,
        "incident_data": incident_data,
        "recent_metrics": recent_metrics,
        "anomalies": anomalies,
        "process_snapshots": process_snapshots,
        "valid": True,
        "validation_notes": [],
        "correlation_score": correlation_score,
        "time_span_minutes": 0.0,
        "affected_metrics": [],
        "evidence": [],
        "assessed_severity": "WARNING",
        "probable_cause": "",
        "recommended_actions": [],
        "reasoning_summary": "",
        "confidence": 0.5,
        "analysis_source": "rule_based",
        "model_name": None,
        "raw_llm_output": None,
        "errors": [],
    }

    logger.info("analysis_graph_start", incident_id=incident_id)

    try:
        final_state = await graph.ainvoke(initial_state)
        logger.info(
            "analysis_graph_complete",
            incident_id=incident_id,
            source=final_state.get("analysis_source"),
            errors=final_state.get("errors", []),
        )
        return final_state  # type: ignore[return-value]
    except Exception as exc:
        logger.error("analysis_graph_error", incident_id=incident_id, error=str(exc))
        # Return the initial state with the error recorded
        initial_state["errors"] = [f"Graph execution failed: {exc}"]
        initial_state["analysis_source"] = "rule_based"
        return initial_state
