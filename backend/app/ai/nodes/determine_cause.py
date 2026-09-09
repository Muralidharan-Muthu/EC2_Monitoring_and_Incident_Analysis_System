"""Node 4: Determine probable cause using Groq LLM with rule-based fallback."""

from __future__ import annotations

from typing import Any

from app.ai.state import IncidentAnalysisState
from app.ai.groq_client import call_groq_for_analysis
from app.ai.prompts import build_analysis_prompt
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.analysis import LLMAnalysisOutput
from app.services.correlation_engine import generate_rule_based_cause

logger = get_logger(__name__)


def determine_cause_node(state: IncidentAnalysisState) -> dict[str, Any]:
    """
    Use Groq LLM to determine probable cause.

    If the LLM is unavailable or returns invalid output, falls back to
    deterministic rule-based analysis. The monitoring system never fails
    due to LLM unavailability.
    """
    incident_data = state.get("incident_data", {})
    anomalies = state.get("anomalies", [])
    recent_metrics = state.get("recent_metrics", [])
    process_snapshots = state.get("process_snapshots", [])
    correlation_score = state.get("correlation_score", 0.0)
    errors = list(state.get("errors", []))

    # Generate rule-based cause for LLM context and fallback
    rule_cause = incident_data.get("probable_cause", "")
    if not rule_cause:
        # Build from anomaly data
        from app.models.anomaly import Anomaly  # avoid circular at module level

        class _MockAnomaly:
            def __init__(self, d: dict) -> None:
                self.metric_name = d.get("metric_name", "")
                self.is_persistent = d.get("is_persistent", False)

        mock_anomalies = [_MockAnomaly(a) for a in anomalies]
        rule_cause = generate_rule_based_cause(mock_anomalies)  # type: ignore[arg-type]

    # Build prompt
    prompt_messages = build_analysis_prompt(
        incident=incident_data,
        anomalies=anomalies,
        recent_metrics=recent_metrics,
        process_snapshots=process_snapshots,
        correlation_score=correlation_score,
        rule_based_cause=rule_cause,
    )

    # Call LLM
    llm_output, error = call_groq_for_analysis(prompt_messages)

    if error:
        errors.append(f"LLM unavailable: {error}")
        logger.warning("llm_fallback_triggered", reason=error)
        return {
            "probable_cause": rule_cause,
            "analysis_source": "rule_based",
            "raw_llm_output": None,
            "errors": errors,
        }

    # Validate LLM output with Pydantic
    try:
        validated = LLMAnalysisOutput(**llm_output)  # type: ignore[arg-type]
        settings = get_settings()
        logger.info("llm_analysis_validated", model=settings.groq_model)
        return {
            "probable_cause": validated.probable_cause,
            "evidence": validated.evidence,
            "recommended_actions": validated.recommended_actions,
            "assessed_severity": validated.severity,
            "confidence": validated.confidence,
            "reasoning_summary": validated.reasoning_summary or "",
            "analysis_source": "llm",
            "model_name": settings.groq_model,
            "raw_llm_output": llm_output,
            "errors": errors,
        }
    except Exception as exc:
        error_msg = f"LLM output validation failed: {exc}"
        errors.append(error_msg)
        logger.warning("llm_validation_failed", error=error_msg)
        return {
            "probable_cause": rule_cause,
            "analysis_source": "rule_based",
            "raw_llm_output": llm_output,
            "errors": errors,
        }
