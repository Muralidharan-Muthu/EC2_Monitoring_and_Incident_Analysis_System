"""
Node 4: Assess Severity.
Evaluates deterministic 4-tier incident severity and produces findings.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.ai.state import IncidentAnalysisState


def assess_severity(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Deterministically assess incident severity based on metric diversity,
    concurrency, and persistence.
    """
    anomalies = state.get("anomalies", [])
    metrics = set(state.get("affected_metrics", []))

    critical_count = sum(1 for a in anomalies if a.get("severity") == "CRITICAL")
    warning_count = sum(1 for a in anomalies if a.get("severity") == "WARNING")
    has_persistent = any(a.get("is_persistent") for a in anomalies)

    findings: List[str] = []

    # Severity evaluation rules
    if len(metrics) >= 4 or (
        "cpu_usage" in metrics
        and "memory_usage" in metrics
        and ("load_1m" in metrics or "response_time_ms" in metrics)
    ):
        severity = "CRITICAL"
        findings.append("Full multi-subsystem resource saturation detected across CPU, memory, and load/latency.")
    elif critical_count >= 1 and (has_persistent or critical_count >= 2):
        severity = "HIGH"
        findings.append(f"Sustained or multiple critical threshold violations detected ({critical_count} critical).")
    elif warning_count > 1 or critical_count == 1:
        severity = "MEDIUM"
        findings.append(f"Multiple warning threshold violations observed across {len(metrics)} subsystems.")
    else:
        severity = "LOW"
        findings.append("Single isolated warning anomaly.")

    return {
        "deterministic_severity": severity,
        "assessed_severity": severity,
        "deterministic_findings": findings,
    }
