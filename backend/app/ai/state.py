"""
Typed state for the 8-node LangGraph incident analysis workflow.

State flows through:
START -> context -> evidence -> correlation -> severity -> root_cause -> recommendation -> summary -> validation -> END
"""

from __future__ import annotations

from typing import Any, List, Optional
from typing_extensions import TypedDict


class IncidentAnalysisState(TypedDict, total=False):
    """
    Shared state passed between all 8 LangGraph nodes.
    """

    # Identifiers
    incident_id: str
    host: str
    hostname: str

    # Raw context loaded from DB & collectors
    incident_data: dict[str, Any]
    recent_metrics: List[dict[str, Any]]
    anomalies: List[dict[str, Any]]
    process_evidence: List[dict[str, Any]]
    log_evidence: List[dict[str, Any]]

    # Step 2: Evidence validation
    valid: bool
    validation_notes: List[str]
    evidence: List[str]

    # Step 3: Correlation
    correlation_score: float
    affected_metrics: List[str]
    time_span_minutes: float

    # Step 4: Severity
    deterministic_severity: str
    assessed_severity: str
    deterministic_findings: List[str]

    # Step 5: Root Cause
    probable_cause: str

    # Step 6: Recommendations
    recommended_actions: List[str]

    # Step 7: Summary
    reasoning_summary: str
    final_summary: str
    confidence: float
    analysis_source: str  # "groq" | "rule_engine"
    model_name: Optional[str]

    # Step 8: Validation
    validation_passed: bool
    structured_output: dict[str, Any]
    raw_llm_output: Optional[dict[str, Any]]

    # Diagnostics
    errors: List[str]
