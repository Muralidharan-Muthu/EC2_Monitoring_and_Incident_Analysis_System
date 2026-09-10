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

    # Fallback cause and event relationship text
    fallback_cause = _generate_rule_based_cause(state)
    fallback_relationship = _generate_rule_based_relationship(state)

    # If Groq is not configured, proceed directly with deterministic engine
    if not settings.groq_api_key:
        return {
            "probable_cause": fallback_cause,
            "event_relationship": fallback_relationship,
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
            "event_relationship": fallback_relationship,
            "analysis_source": "rule_engine",
            "model_name": None,
            "confidence": 0.80,
            "raw_llm_output": None,
            "errors": errors,
        }

    # Extract cause and event relationship from Groq structured response
    probable_cause = parsed_json.get("probable_cause") or fallback_cause
    event_relationship = parsed_json.get("event_relationship") or fallback_relationship
    confidence = float(parsed_json.get("confidence", 0.90))

    return {
        "probable_cause": probable_cause,
        "event_relationship": event_relationship,
        "analysis_source": "groq",
        "model_name": settings.groq_model,
        "confidence": confidence,
        "raw_llm_output": parsed_json,
        "errors": errors,
    }


def _generate_rule_based_relationship(state: IncidentAnalysisState) -> str:
    """Analyze whether multi-metric anomalies across time are causally linked."""
    metrics = set(state.get("affected_metrics", []))

    if {"cpu_usage", "memory_usage", "response_time_ms"}.issubset(metrics):
        return (
            "Events Confirmed Related (Cascading Failure): Simultaneous CPU and Memory exhaustion "
            "directly starves application worker threads of CPU cycles and memory pages. "
            "This creates an execution bottleneck that directly causes the observed spike in Response Time, "
            "proving all anomalies stem from a single cascading failure rather than isolated events."
        )
    if {"cpu_usage", "memory_usage", "load_1m"}.issubset(metrics):
        return (
            "Events Confirmed Related (Resource Exhaustion Cascade): High CPU consumption paired with memory pressure "
            "causes scheduler queue backlog, directly driving elevated System Load. All observed metrics are tightly "
            "coupled manifestations of a single system-wide saturation incident."
        )
    if {"cpu_usage", "load_1m"}.issubset(metrics):
        return (
            "Events Confirmed Related: System Load is a direct mathematical consequence of runnable processes queued for "
            "the saturated CPU cores. These are not separate alerts, but the same CPU constraint viewed from resource "
            "and scheduler perspectives."
        )
    if len(metrics) > 1:
        return (
            f"Events Correlated: {len(metrics)} subsystems ({', '.join(sorted(metrics))}) exhibited concurrent abnormal "
            "readings within the same correlation window. Unified into a single incident to prevent alert fatigue."
        )
    return "Single isolated metric anomaly."


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

