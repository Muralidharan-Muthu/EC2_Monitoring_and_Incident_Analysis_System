"""
LangGraph workflow for incident analysis.

Exact 8-node architecture per specification:
  START
    ↓
  Collect Incident Context
    ↓
  Validate Evidence
    ↓
  Correlate Related Events
    ↓
  Assess Severity
    ↓
  Determine Probable Cause
    ↓
  Generate Recommended Actions
    ↓
  Generate Incident Summary
    ↓
  Validate Structured Output
    ↓
  END
"""

from __future__ import annotations

from typing import Any, List, Optional
from langgraph.graph import END, START, StateGraph

from app.ai.nodes.context import collect_incident_context
from app.ai.nodes.correlation import correlate_events
from app.ai.nodes.evidence import validate_evidence
from app.ai.nodes.recommendation import generate_recommendations
from app.ai.nodes.root_cause import determine_root_cause
from app.ai.nodes.severity import assess_severity
from app.ai.nodes.summary import generate_incident_summary
from app.ai.nodes.validation import validate_structured_output
from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_analysis_graph() -> Any:
    """
    Assemble and compile the 8-node incident analysis LangGraph.
    """
    graph = StateGraph(IncidentAnalysisState)

    # 1. Register 8 nodes
    graph.add_node("collect_context", collect_incident_context)
    graph.add_node("validate_evidence", validate_evidence)
    graph.add_node("correlate_events", correlate_events)
    graph.add_node("assess_severity", assess_severity)
    graph.add_node("determine_root_cause", determine_root_cause)
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("generate_summary", generate_incident_summary)
    graph.add_node("validate_output", validate_structured_output)

    # 2. Wire sequential flow
    graph.add_edge(START, "collect_context")
    graph.add_edge("collect_context", "validate_evidence")
    graph.add_edge("validate_evidence", "correlate_events")
    graph.add_edge("correlate_events", "assess_severity")
    graph.add_edge("assess_severity", "determine_root_cause")
    graph.add_edge("determine_root_cause", "generate_recommendations")
    graph.add_edge("generate_recommendations", "generate_summary")
    graph.add_edge("generate_summary", "validate_output")
    graph.add_edge("validate_output", END)

    return graph.compile()


_compiled_graph = None


def get_analysis_graph():
    """Return the compiled singleton graph."""
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
    process_snapshots: Optional[list[dict[str, Any]]] = None,
    log_evidence: Optional[list[dict[str, Any]]] = None,
    correlation_score: float = 0.0,
) -> IncidentAnalysisState:
    """
    Execute the 8-node LangGraph incident analysis workflow.
    """
    graph = get_analysis_graph()

    initial_state: IncidentAnalysisState = {
        "incident_id": str(incident_id),
        "host": hostname,
        "hostname": hostname,
        "incident_data": incident_data or {},
        "recent_metrics": recent_metrics or [],
        "anomalies": anomalies or [],
        "process_evidence": process_snapshots or [],
        "log_evidence": log_evidence or [],
        "correlation_score": correlation_score,
        "errors": [],
    }

    logger.info("langgraph_analysis_start", incident_id=str(incident_id), host=hostname)

    try:
        final_state = await graph.ainvoke(initial_state)
        logger.info(
            "langgraph_analysis_complete",
            incident_id=str(incident_id),
            source=final_state.get("analysis_source"),
            severity=final_state.get("assessed_severity"),
        )
        return final_state
    except Exception as exc:
        logger.error("langgraph_analysis_failed", incident_id=str(incident_id), error=str(exc))
        initial_state["errors"] = [f"LangGraph execution exception: {exc}"]
        initial_state["analysis_source"] = "rule_engine"
        initial_state["probable_cause"] = "Deterministic fallback due to workflow exception."
        initial_state["recommended_actions"] = ["Review system telemetry directly."]
        initial_state["confidence"] = 0.60
        initial_state["assessed_severity"] = "WARNING"
        return initial_state
