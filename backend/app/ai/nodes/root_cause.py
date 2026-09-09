"""
Node 5: Determine Probable Cause.
Enhances analysis with Groq LLM when available; falls back to deterministic rules.
"""

from __future__ import annotations

from typing import Any, Dict
from app.ai.groq_client import call_groq_for_analysis
from app.ai.prompts import build_analysis_prompt
from app.ai.state import IncidentAnalysisState
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def determine_root_cause(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Determine probable cause via Groq or deterministic fallback rules.
    """
    settings = get_settings()
    errors = list(state.get("errors", []))

    # Fallback cause text
    fallback_cause = _generate_rule_based_cause(state)

    # If Groq is not configured, proceed directly with deterministic engine
    if not settings.groq_api_key:
        return {
            "probable_cause": fallback_cause,
            "analysis_source": "rule_engine",
            "model_name": None,
            "confidence": 0.85,
            "errors": errors,
        }

    # Attempt Groq analysis
    messages = build_analysis_prompt(
        incident=state.get("incident_data", {}),
        anomalies=state.get("anomalies", []),
        recent_metrics=state.get("recent_metrics", []),
        process_snapshots=state.get("process_evidence", []),
        correlation_score=state.get("correlation_score", 0.0),
        rule_based_cause=fallback_cause,
    )
    parsed_json, err = call_groq_for_analysis(messages)

    if err or not parsed_json:
        logger.warning("groq_fallback_triggered", reason=err)
        errors.append(f"Groq analysis fallback: {err}")
        return {
            "probable_cause": fallback_cause,
            "analysis_source": "rule_engine",
            "model_name": None,
            "confidence": 0.80,
            "raw_llm_output": None,
            "errors": errors,
        }

    # Extract cause from Groq structured response
    probable_cause = parsed_json.get("probable_cause") or fallback_cause
    confidence = float(parsed_json.get("confidence", 0.90))

    return {
        "probable_cause": probable_cause,
        "analysis_source": "groq",
        "model_name": settings.groq_model,
        "confidence": confidence,
        "raw_llm_output": parsed_json,
        "errors": errors,
    }


def _generate_rule_based_cause(state: IncidentAnalysisState) -> str:
    """Deterministic fallback cause."""
    metrics = set(state.get("affected_metrics", []))
    procs = state.get("process_evidence", [])

    proc_info = ""
    if procs:
        top = procs[0]
        name = top.get("name") or top.get("process_name")
        cpu = top.get("cpu_percent", 0)
        mem = top.get("memory_percent", 0)
        proc_info = f" Primary suspect process is '{name}' consuming {cpu}% CPU and {mem}% memory."

    if len(metrics) >= 4 or ({"cpu_usage", "memory_usage", "load_1m"}.issubset(metrics)):
        return (
            "Probable cause: Severe multi-subsystem resource saturation across compute, memory, "
            f"and operating system queues. Evidence suggests intense concurrent workload.{proc_info}"
        )
    if "cpu_usage" in metrics and "load_1m" in metrics:
        return (
            "Probable cause: Elevated CPU utilization and system load average exceeding CPU core capacity. "
            f"Evidence suggests an intensive compute job or runaway thread.{proc_info}"
        )
    if "memory_usage" in metrics:
        return (
            "Probable cause: Memory exhaustion with available system memory critically low. "
            f"Likely related to unconstrained memory allocation or memory leak.{proc_info}"
        )
    if "disk_usage" in metrics:
        return (
            "Probable cause: Storage volume approaching capacity limit. "
            "Likely caused by accumulating system logs or uncleaned cache files."
        )

    return f"Probable cause: Correlated abnormal readings observed in {', '.join(sorted(metrics))}."
