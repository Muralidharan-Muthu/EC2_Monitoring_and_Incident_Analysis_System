"""
Prompt templates for the Groq LLM incident analysis.

Prompts are constructed from structured evidence — never from raw logs
or unvalidated input. The LLM receives only the information it needs.
"""

from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are an expert AWS EC2 infrastructure reliability engineer 
analyzing a system incident. Your role is to review validated, rule-detected 
metric anomalies and provide reasoned, evidence-based incident analysis.

IMPORTANT RULES:
1. Base your analysis ONLY on the evidence provided. Do not speculate beyond the data.
2. Never present probable causes as guaranteed facts — use language like 
   "probable cause", "likely contributing factor", "evidence suggests".
3. Return ONLY valid JSON matching the exact schema specified. No markdown, no extra text.
4. Confidence should reflect how much evidence supports your conclusions (0.0 to 1.0).
5. Be specific and actionable in recommended_actions.
"""

ANALYSIS_SCHEMA = """{
  "severity": "WARNING or CRITICAL",
  "affected_metrics": ["list of metric names like CPU, Memory, Disk, System Load, Response Time"],
  "probable_cause": "Evidence-based probable cause description using appropriate hedging language",
  "evidence": ["List of specific observed evidence items"],
  "recommended_actions": ["List of specific, actionable remediation steps"],
  "confidence": 0.85,
  "reasoning_summary": "Brief narrative explaining how the evidence leads to the probable cause"
}"""


def _fmt_float(val: Any, prec: int = 1) -> str:
    """Safely format float values without throwing on strings or None."""
    if val is None or val == "?":
        return "?"
    try:
        return f"{float(val):.{prec}f}"
    except (ValueError, TypeError):
        return str(val)


def build_analysis_prompt(
    incident: dict[str, Any],
    anomalies: list[dict[str, Any]],
    recent_metrics: list[dict[str, Any]],
    process_snapshots: list[dict[str, Any]],
    correlation_score: float,
    rule_based_cause: str = "",
    **kwargs: Any,
) -> list[dict[str, str]]:
    """
    Build the complete prompt message list for the Groq analysis call.

    Structures only relevant evidence — not the entire database dump.
    """

    # Format anomalies
    anomaly_lines = []
    for a in anomalies[:10]:  # Limit to 10 most relevant
        obs = _fmt_float(a.get("observed_value"))
        thresh = _fmt_float(a.get("threshold"))
        persistent = "(PERSISTENT)" if a.get("is_persistent") else ""
        anomaly_lines.append(
            f"  - {a.get('metric_name', 'unknown')}: "
            f"observed {obs}, "
            f"threshold {thresh} "
            f"[{a.get('severity', '?')}] {persistent}".strip()
        )

    # Format recent metric trend
    metric_lines = []
    for m in recent_metrics[-5:]:  # Last 5 observations
        cpu = _fmt_float(m.get("cpu_usage"))
        mem = _fmt_float(m.get("memory_usage"))
        disk = _fmt_float(m.get("disk_usage"))
        load = _fmt_float(m.get("load_1m"), prec=2)
        metric_lines.append(
            f"  {m.get('timestamp', '?')}: CPU={cpu}% MEM={mem}% DISK={disk}% LOAD={load}"
        )

    # Format processes
    proc_lines = []
    for p in process_snapshots[:4]:
        proc_lines.append(
            f"  - [{p.get('snapshot_type', '?')}] "
            f"{p.get('process_name', '?')} "
            f"(CPU: {p.get('cpu_percent', '?')}%, "
            f"MEM: {p.get('memory_percent', '?')}%)"
        )

    score_str = _fmt_float(correlation_score)
    user_content = f"""INCIDENT ANALYSIS REQUEST

Incident ID: {incident.get('id', 'N/A')}
Hostname: {incident.get('hostname', 'N/A')}
Started: {incident.get('started_at', 'N/A')}
Observation Count: {incident.get('observation_count', 1)}
Correlation Score: {score_str}

DETECTED ANOMALIES:
{chr(10).join(anomaly_lines) if anomaly_lines else "  None"}

RECENT METRIC TREND (last 5 observations):
{chr(10).join(metric_lines) if metric_lines else "  No recent data"}

TOP RESOURCE-CONSUMING PROCESSES:
{chr(10).join(proc_lines) if proc_lines else "  No process data available"}

RULE-BASED PRELIMINARY ASSESSMENT:
{rule_based_cause}

Please analyze the above evidence and return a JSON response matching this schema exactly:
{ANALYSIS_SCHEMA}
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


build_incident_analysis_prompt = build_analysis_prompt
