"""
Node 6: Generate Recommended Actions.
Extracts LLM recommendations or generates deterministic remediation guidance.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.ai.state import IncidentAnalysisState


def generate_recommendations(state: IncidentAnalysisState) -> Dict[str, Any]:
    """
    Produce actionable operational recommendations.
    """
    # 1. Check if LLM produced valid recommendations
    raw = state.get("raw_llm_output")
    if raw and isinstance(raw.get("recommended_actions"), list) and raw["recommended_actions"]:
        return {"recommended_actions": raw["recommended_actions"]}

    # 2. Rule-based recommendations
    metrics = set(state.get("affected_metrics", []))
    actions: List[str] = []

    if "cpu_usage" in metrics or "load_1m" in metrics:
        actions.append("Inspect top CPU processes: `ps -eo pid,comm,%cpu --sort=-%cpu | head -n 10`")
    if "memory_usage" in metrics:
        actions.append("Inspect memory consumers and buffers: `free -m` and `ps -eo pid,comm,%mem --sort=-%mem | head -n 10`")
    if "disk_usage" in metrics:
        actions.append("Check disk usage hotspots: `df -h /` and `du -sh /var/log/*`")
    if "response_time_ms" in metrics:
        actions.append("Investigate web server latency and application connection pools")

    actions.append("Examine system journal: `journalctl -p warning..err -n 50 --no-pager`")
    actions.append("Evaluate EC2 instance sizing and scale vertically if workload is expected to persist")

    return {"recommended_actions": actions}
