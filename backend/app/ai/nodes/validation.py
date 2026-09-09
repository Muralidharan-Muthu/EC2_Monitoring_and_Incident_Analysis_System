"""
Node 8: Validate Structured Output.
Validates the synthesized analysis results against the LLMAnalysisOutput Pydantic schema.
"""

from __future__ import annotations

from typing import Any, Dict
from pydantic import ValidationError

from app.ai.state import IncidentAnalysisState
from app.core.logging import get_logger
from app.schemas.analysis import LLMAnalysisOutput

logger = get_logger(__name__)


def validate_structured_output(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Validate and format the final analysis output against Pydantic schema.
    """
    errors = list(state.get("errors", []))

    payload = {
        "severity": state.get("assessed_severity", "WARNING"),
        "affected_metrics": state.get("affected_metrics", []),
        "probable_cause": state.get("probable_cause", "Resource saturation"),
        "evidence": state.get("evidence", ["Evidence collected from EC2 monitoring metrics"]),
        "recommended_actions": state.get("recommended_actions", ["Review system telemetry"]),
        "confidence": float(state.get("confidence", 0.85)),
        "reasoning_summary": state.get("reasoning_summary") or state.get("final_summary", ""),
    }

    try:
        validated = LLMAnalysisOutput.model_validate(payload)
        return {
            "validation_passed": True,
            "structured_output": validated.model_dump(),
            "errors": errors,
        }
    except ValidationError as exc:
        logger.warning("structured_output_validation_failed", errors=str(exc))
        errors.append(f"Structured output validation adjusted: {exc}")

        # Safe fallback structure
        fallback_payload = {
            "severity": state.get("assessed_severity", "WARNING"),
            "affected_metrics": state.get("affected_metrics", []),
            "probable_cause": "System resource pressure detected across monitored metrics.",
            "evidence": state.get("evidence", []),
            "recommended_actions": ["Review active processes and system metrics."],
            "confidence": 0.75,
            "reasoning_summary": "Rule engine validated fallback summary.",
        }
        return {
            "validation_passed": False,
            "structured_output": fallback_payload,
            "errors": errors,
        }
