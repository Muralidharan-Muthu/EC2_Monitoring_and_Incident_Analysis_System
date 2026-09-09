# Incident Analysis Engine & AI Workflow Documentation

## 1. Overview

The Incident Analysis Engine combines deterministic, explainable Python rules with an 8-node **LangGraph** workflow powered by **Groq (`qwen/qwen3.8-27b`)**.

A core design principle of this system is **Defense-in-Depth**:
- The system **NEVER** relies entirely on an LLM to detect incidents or determine system health.
- All threshold evaluations, persistence checks, and correlation scores are deterministic.
- The LLM is used as an expert reasoning layer to synthesize observed facts into human-readable narratives, root cause hypotheses, and remediation commands.
- If Groq is unavailable, rate-limited, or misconfigured, the system automatically falls back to deterministic rule analysis without interrupting monitoring.

---

## 2. The 8-Node LangGraph Pipeline

```
START
  ↓
[1] Collect Incident Context  (app/ai/nodes/context.py)
  ↓
[2] Validate Evidence         (app/ai/nodes/evidence.py)
  ↓
[3] Correlate Related Events  (app/ai/nodes/correlation.py)
  ↓
[4] Assess Severity           (app/ai/nodes/severity.py)
  ↓
[5] Determine Probable Cause  (app/ai/nodes/root_cause.py)  <--- Groq LLM (qwen/qwen3.8-27b)
  ↓
[6] Generate Recommendations  (app/ai/nodes/recommendation.py)
  ↓
[7] Generate Incident Summary (app/ai/nodes/summary.py)
  ↓
[8] Validate Structured Output(app/ai/nodes/validation.py)  <--- Pydantic Schema Validation
  ↓
END
```

### Node Descriptions:
1. **`collect_incident_context`**: Collects recent metric snapshots, anomaly records, top process snapshots, and system journal logs.
2. **`validate_evidence`**: Separates observed facts from speculation. Formats concrete evidence statements (e.g. `Observed cpu_usage at 94.2%, exceeding critical threshold 90.0%`).
3. **`correlate_events`**: Groups concurrent metric anomalies within a 5-minute sliding window. Computes composite correlation score.
4. **`assess_severity`**: Evaluates 4-tier deterministic severity:
   - `CRITICAL`: Multi-metric saturation (CPU + Memory + Load/Latency).
   - `HIGH`: Persistent critical anomalies.
   - `MEDIUM`: Multiple warning anomalies.
   - `LOW`: Single warning anomaly.
5. **`determine_root_cause`**: Prompts Groq with strict non-hallucination rules and evidence context. If Groq fails, invokes deterministic cause rules.
6. **`generate_recommendations`**: Produces actionable, safe Linux troubleshooting commands (`ps`, `free`, `df`, `journalctl`).
7. **`generate_incident_summary`**: Synthesizes a concise executive narrative.
8. **`validate_structured_output`**: Validates the payload against the `LLMAnalysisOutput` Pydantic model.

---

## 3. Strict Distinction: OBSERVED vs ANALYSIS

In the dashboard and incident detail views, the interface strictly separates:
- **OBSERVED FACTS**:
  - Exact measured values (CPU %, Memory MB, Load 1m, Procs, Logs).
  - Detected anomaly timestamps and thresholds.
- **AI INFERENCE / ANALYSIS**:
  - Probable causes.
  - Recommended actions.
  - Hedged language: "Likely", "Evidence suggests", "Probable cause".
  - Analysis source: `Groq LLM (qwen/qwen3.8-27b)` vs `Rule Engine`.

---

## 4. Demo Incident Scenario

### Simulated Event:
- At 10:00: CPU 92%, Memory 88%, Disk 85%, Load high.
- At 10:05: CPU 96%, Memory 91%, Response Time increased, Load very high.

### Engine Output:
- **Number of Incidents**: Exactly **ONE** incident created (not 5 separate alerts).
- **Incident Key**: Matches family `resource_saturation` on host. Deduplicated.
- **Severity**: `CRITICAL`.
- **Affected Metrics**: `CPU`, `Memory`, `Disk`, `System Load`, `Response Time`.
- **Probable Cause**: "Evidence suggests comprehensive resource saturation affecting CPU, memory, and operating system run queues, likely caused by high-intensity processes or workload exhaustion."
- **Recommended Actions**:
  1. Inspect top CPU consumers: `ps -eo pid,comm,%cpu --sort=-%cpu | head -n 10`
  2. Inspect memory consumers: `ps -eo pid,comm,%mem --sort=-%mem | head -n 10`
  3. Inspect system journal: `journalctl -p warning..err -n 50 --no-pager`
  4. Evaluate EC2 instance sizing.
