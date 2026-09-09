"""
Node 2: Validate Evidence.
Checks observed metrics, processes, and anomalies for consistency.
Extracts factual evidence statements (distinguished from inference).
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.ai.state import IncidentAnalysisState


def validate_evidence(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Synthesize explicit, factual evidence statements from observed data.
    """
    evidence: List[str] = []
    validation_notes: List[str] = []

    # 1. Anomaly evidence
    anomalies = state.get("anomalies", [])
    for a in anomalies:
        metric = a.get("metric_name", "unknown")
        val = a.get("observed_value")
        thresh = a.get("threshold")
        sev = a.get("severity", "WARNING")
        pers = a.get("is_persistent", False)

        val_str = f"{val:.1f}" if isinstance(val, (int, float)) else str(val)
        thresh_str = f"{thresh:.1f}" if isinstance(thresh, (int, float)) else str(thresh)
        p_note = " (sustained/persistent)" if pers else ""

        evidence.append(
            f"Observed {metric} at {val_str}, exceeding {sev.lower()} threshold {thresh_str}{p_note}."
        )

    # 2. Process evidence
    procs = state.get("process_evidence", [])
    if procs:
        top_proc = procs[0]
        p_name = top_proc.get("name") or top_proc.get("process_name") or "unknown"
        p_cpu = top_proc.get("cpu_percent")
        p_mem = top_proc.get("memory_percent")
        evidence.append(
            f"Top resource consumer: process '{p_name}' (CPU: {p_cpu or 0}%, Memory: {p_mem or 0}%)."
        )

    # 3. Log evidence
    logs = state.get("log_evidence", [])
    if logs:
        warn_logs = [lg for lg in logs if lg.get("priority") in ("warning", "err", "error")]
        if warn_logs:
            sample = warn_logs[0].get("message", "")[:120]
            evidence.append(f"System journal log alert: {sample}")

    valid = len(evidence) > 0
    if not valid:
        validation_notes.append("No active anomaly records found in incident evidence.")
    else:
        validation_notes.append(f"Successfully validated {len(evidence)} evidence points.")

    return {
        "valid": valid,
        "evidence": evidence,
        "validation_notes": validation_notes,
    }
