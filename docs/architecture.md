# Architecture Documentation

## EC2 Monitoring and Incident Analysis System

![Architecture Diagram](./architecture.png)

---

## System Overview

The EC2 Monitoring and Incident Analysis System is composed of four distinct layers, each with a single well-defined responsibility:

| Layer | Component | Responsibility |
|---|---|---|
| Collection | Python Monitoring Agent | Gather raw system metrics from Linux |
| Detection | Rule-Based Anomaly Detector | Determine threshold violations deterministically |
| Correlation | Correlation Engine | Group related anomalies into incidents |
| Reasoning | LangGraph + Groq LLM | Generate human-readable explanations |
| Presentation | React Dashboard | Display live data and incident analysis |

---

## Why Separate Collection, Detection, Correlation, and AI Analysis?

### Collection is separate from detection
The monitoring agent's only job is to faithfully report what the system is doing. It does not make any judgement about whether values are abnormal. This separation means:
- The agent can be replaced or rewritten without touching the detection logic.
- Detection thresholds can be changed in the backend without redeploying the agent.
- The agent remains simple and resilient.

### Detection is separate from correlation
A single high CPU reading is not necessarily an incident. The detector finds individual threshold violations; the correlation engine decides whether multiple violations across a time window constitute a single compound event.

This prevents alert storms — a classic problem where monitoring systems fire one alert per anomalous metric, flooding on-call engineers with dozens of notifications for a single root cause.

### Correlation is separate from AI reasoning
The correlation engine applies deterministic, auditable rules:
- Time-window proximity
- Weighted metric scoring
- Incident deduplication by key

This produces a structured evidence set. The AI layer receives this evidence and produces a human-readable explanation. If the LLM is unavailable, the deterministic analysis is already complete — monitoring never depends on the LLM.

### AI reasoning is separate from presentation
The React dashboard displays whatever analysis is available — LLM-generated or rule-based — without embedding any business logic.

---

## Component Descriptions

### Python Monitoring Agent

Runs **on the EC2 Linux instance**. Collects system metrics using:
- `psutil` — cross-platform CPU, memory, disk, network, process information
- `/proc` filesystem — Linux-specific kernel metrics
- `subprocess` with an explicit allowlist — safe execution of `journalctl` for log inspection

Sends a structured JSON payload to the FastAPI backend every N seconds (configurable). Retries on network failure. Never crashes due to a single collector failing.

### FastAPI Backend

The central hub. Responsibilities:
1. **Metric ingestion** — validate and persist incoming agent payloads
2. **Anomaly detection** — immediately after ingestion, runs rule-based checks
3. **Incident management** — correlates anomalies, deduplicates incidents, manages lifecycle
4. **LangGraph orchestration** — on demand, runs the AI analysis workflow
5. **REST API** — serves data to the React frontend

Uses async SQLAlchemy with PostgreSQL for all database operations.

### Rule-Based Anomaly Detector

```
Metric Value → Threshold Check → Severity (WARNING | CRITICAL)
                              → Persistence Check (N consecutive samples)
                              → DetectedAnomaly
```

Thresholds are configurable via environment variables. Persistence state is tracked in-memory per (hostname, metric_name) pair.

### Correlation Engine

```
[Anomaly_1, Anomaly_2, Anomaly_3] within time window
    → compute_incident_key (SHA-256 of hostname + sorted metrics)
    → compute_correlation_score (weighted sum)
    → determine_severity (worst of constituent anomalies)
    → build_incident_title
    → generate_rule_based_cause (pattern matching)
    → generate_rule_based_recommendation
```

The `incident_key` ensures that the same set of failing metrics always maps to the same incident, preventing duplicates.

### LangGraph Workflow

6-node directed acyclic graph:

```
START
  ↓
collect_context     — Validate input data is present
  ↓
correlate           — Build evidence list from anomalies and metrics
  ↓
determine_severity  — Assess severity from anomaly severities and score
  ↓
determine_cause     — Call Groq LLM; fall back to rule-based if unavailable
  ↓
recommend_action    — Ensure recommendations are populated
  ↓
generate_summary    — Compose final reasoning narrative
  ↓
END
```

### Groq LLM Integration

- Model: configurable via `GROQ_MODEL` environment variable
- Used for: reasoning and human-readable explanation
- NOT used for: threshold detection, persistence detection, severity determination, incident deduplication
- Failure handling: 2 retries → rule-based fallback
- Output validation: Pydantic `LLMAnalysisOutput` schema

### Supabase PostgreSQL

Standard PostgreSQL hosted on Supabase. The system uses SQLAlchemy ORM and treats Supabase as managed PostgreSQL with no Supabase-specific features.

Schema:
```
metrics
  └── process_snapshots (many per metric)
  └── anomalies (many per metric)
        └── incident_anomalies (M:M join)
              └── incidents
                    └── incident_analyses (1:1)
```

### React Dashboard

- **Dashboard** — live system status, metric cards, trend charts, recent incidents
- **Metrics** — historical charts with time range selection (15m / 1h / 6h / 24h)
- **Incidents** — filterable incident list
- **Incident Detail** — full analysis with observed facts, AI reasoning, and recommended actions

Auto-refreshes every 10 seconds (configurable via `VITE_POLL_INTERVAL_MS`).

---

## Data Flow

```
EC2 Linux Instance
        │
        │ (every 30 seconds)
        ↓
Python Agent collects:
  cpu_usage, memory_usage, disk_usage, load_*,
  top_cpu_process, top_memory_process, network_*
        │
        │ HTTP POST /api/metrics
        │ Header: X-API-Key
        ↓
FastAPI /api/metrics route
        │
        ├─→ Persist Metric record
        ├─→ Persist ProcessSnapshot records
        ├─→ AnomalyDetector.detect_anomalies()
        │        └─→ Persist Anomaly records
        └─→ IncidentService.process_anomalies()
                 ├─→ Compute incident_key
                 ├─→ Lookup existing active incident
                 ├─→ Create or update Incident
                 └─→ Link Anomalies to Incident
                          │
                          │ (on demand: POST /api/incidents/{id}/analyze)
                          ↓
                 LangGraph.run_incident_analysis()
                          │
                          ├─→ collect_context node
                          ├─→ correlate node
                          ├─→ determine_severity node
                          ├─→ determine_cause node → Groq LLM
                          ├─→ recommend_action node
                          └─→ generate_summary node
                                   │
                                   ↓
                          IncidentAnalysis persisted
                                   │
                                   │ React polls every 10s
                                   ↓
                          Dashboard renders analysis
```

---

## Security Considerations

- All credentials in environment variables, never in code
- API key validation on the `/api/metrics` ingestion endpoint
- CORS configured to specific frontend origins
- Input validation via Pydantic on all API endpoints
- No secrets logged or exposed in error messages
- Supabase connection uses SSL by default

---

## Scalability Notes

The current architecture is designed for a single EC2 instance demonstration. For production use with multiple instances:
- The monitoring agent would report `hostname` allowing per-host incident tracking
- The correlation engine already namespaces by `hostname`
- PostgreSQL partitioning by `timestamp` would improve query performance at scale
- See README Future Improvements for the full list
