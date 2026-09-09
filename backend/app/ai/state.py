"""
Typed state for the LangGraph incident analysis workflow.

Each node in the graph reads from and writes to this state object.
Using TypedDict ensures type safety throughout the graph.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class IncidentAnalysisState(TypedDict):
    """
    Shared state passed between all LangGraph nodes.

    Fields are progressively populated as the graph executes.
    """

    # ---- Input ----
    incident_id: str
    hostname: str

    # Raw data loaded from the database
    incident_data: dict[str, Any]
    recent_metrics: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]
    process_snapshots: list[dict[str, Any]]

    # ---- Intermediate results ----
    # Validation step
    valid: bool
    validation_notes: list[str]

    # Correlation step
    correlation_score: float
    time_span_minutes: float
    affected_metrics: list[str]
    evidence: list[str]

    # Severity assessment
    assessed_severity: str

    # Root cause determination
    probable_cause: str

    # Recommended actions
    recommended_actions: list[str]

    # ---- Output ----
    reasoning_summary: str
    confidence: float
    analysis_source: str  # "llm" | "rule_based"
    model_name: Optional[str]

    # Raw LLM output for debugging
    raw_llm_output: Optional[dict[str, Any]]

    # Error tracking — allows graceful degradation
    errors: list[str]
