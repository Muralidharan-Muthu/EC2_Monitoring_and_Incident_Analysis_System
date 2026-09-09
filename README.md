# EC2 Monitoring and Incident Analysis System

A production-style observability platform that monitors a Linux-based AWS EC2 instance, detects anomalous behavior using deterministic rules, correlates related anomalies into incidents, and uses a **LangGraph + Groq LLM** workflow to generate evidence-based incident analysis.

---

## Problem Statement

Traditional monitoring tools produce one alert per threshold violation, leading to **alert storms** where a single root cause generates dozens of notifications. Engineers need to manually correlate these alerts to understand what is actually happening.

This system solves that problem by:
1. Detecting individual metric anomalies deterministically
2. **Correlating** related anomalies within a time window into a **single incident**
3. Using **AI reasoning** to generate a human-readable explanation of what happened and why
4. Presenting everything in a clean, professional dashboard

---

## Features

- ✅ Real-time Linux system monitoring (CPU, Memory, Disk, Load, Network, Processes)
- ✅ Rule-based anomaly detection with configurable thresholds
- ✅ Persistence detection (N consecutive samples before incident creation)
- ✅ Temporal correlation engine — multiple anomalies → one incident
- ✅ Incident deduplication — same ongoing condition updates one incident
- ✅ Incident lifecycle (OPEN → INVESTIGATING → RESOLVED)
- ✅ LangGraph 6-node analysis workflow
- ✅ Groq LLM integration for evidence-based reasoning
- ✅ Graceful LLM fallback — monitoring never depends on AI availability
- ✅ React dashboard with live metrics and incident detail pages
- ✅ Process snapshot tracking (top CPU/memory processes)
- ✅ Optional HTTP response time monitoring
- ✅ Safe Linux log inspection via journalctl
- ✅ Comprehensive test suite

---

## Architecture

![Architecture](./docs/architecture.png)

See [docs/architecture.md](./docs/architecture.md) for detailed explanation.

```
EC2 Linux Instance
        │
        ▼ (HTTP POST every 30s)
Python Monitoring Agent
        │
        ▼
FastAPI Backend
        ├── Rule-Based Anomaly Detector
        ├── Persistence Tracker
        ├── Correlation Engine ──→ Incident Manager
        └── Supabase PostgreSQL
                │
                ▼ (on demand)
        LangGraph Workflow
                └── Groq LLM (reasoning)
                        │
                        ▼
                React Dashboard
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Monitoring Agent | Python, psutil, httpx, tenacity |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL on Supabase |
| AI | LangGraph, Groq API, llama-3.3-70b-versatile |
| Frontend | React, Vite, TypeScript, Recharts, Axios |
| Auth | API key header (X-API-Key) |

---

## Project Structure

```
ec2-monitoring-system/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # FastAPI route handlers (thin)
│   │   ├── ai/                 # LangGraph workflow + Groq client
│   │   │   └── nodes/          # Individual graph nodes
│   │   ├── core/               # Config, DB, logging, security
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── repositories/       # Database access layer
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic
│   │   ├── tests/              # Unit and integration tests
│   │   └── main.py             # Application entry point
│   ├── alembic/                # Database migrations
│   ├── requirements.txt
│   └── .env.example
│
├── agent/
│   ├── collectors/             # Individual metric collectors
│   │   ├── cpu.py              # CPU + load average
│   │   ├── memory.py           # Memory usage
│   │   ├── disk.py             # Disk usage
│   │   ├── network.py          # Network I/O
│   │   ├── process.py          # Top processes
│   │   ├── system.py           # Hostname, OS info
│   │   ├── logs.py             # journalctl log inspection
│   │   └── load.py             # Optional HTTP response time
│   ├── monitor_agent.py        # Main agent entry point
│   ├── sender.py               # HTTP delivery with retry
│   ├── config.py               # Environment configuration
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── hooks/              # Custom React hooks with polling
│   │   ├── pages/              # Dashboard, Metrics, Incidents, Detail
│   │   ├── services/           # API client functions
│   │   ├── types/              # TypeScript type definitions
│   │   ├── App.tsx             # Router + sidebar navigation
│   │   └── main.tsx            # React entry point
│   ├── package.json
│   └── .env.example
│
├── docs/
│   ├── architecture.md
│   └── architecture.png
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Linux Monitoring Approach

The monitoring agent uses a layered approach:

### psutil (primary)
Cross-platform Python library providing:
- `cpu_percent()` — CPU usage with 1-second measurement interval
- `virtual_memory()` — Memory usage and available bytes
- `disk_usage()` — Disk usage for mount point
- `net_io_counters()` — Network bytes sent/received
- `process_iter()` — Per-process CPU and memory usage
- `getloadavg()` — 1/5/15-minute load averages

### Linux system commands (supplementary, via allowlist)
Only commands in the explicit allowlist may be executed:
- `journalctl` — recent error/warning log entries

The allowlist prevents arbitrary command execution. All subprocess calls use `timeout`, `capture_output=True`, and `check=False` to handle failures safely.

---

## Monitoring Agent

### Configuration

```bash
cd agent
cp .env.example .env
# Edit .env with your backend URL and API key
```

### Running on EC2

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python monitor_agent.py
```

The agent:
1. Collects metrics every `COLLECTION_INTERVAL_SECONDS` (default: 30)
2. Sends a JSON payload to `BACKEND_URL/api/metrics`
3. Retries up to `MAX_RETRIES` times with exponential backoff
4. Continues operating if individual collectors fail
5. Gracefully stops on SIGTERM/SIGINT

### Agent Payload Format

```json
{
  "hostname": "ec2-prod-01",
  "timestamp": "2026-09-09T10:00:00Z",
  "cpu_usage": 92.4,
  "memory_usage": 88.1,
  "disk_usage": 85.0,
  "load_1m": 4.2,
  "load_5m": 3.8,
  "load_15m": 3.1,
  "cpu_count": 2,
  "memory_available_mb": 210.0,
  "disk_free_gb": 3.1,
  "network_rx_bytes": 123456,
  "network_tx_bytes": 987654,
  "top_cpu_process": "python3",
  "top_cpu_percent": 87.4,
  "top_memory_process": "python3",
  "top_memory_percent": 41.2,
  "response_time_ms": 2100.0,
  "http_status": 200
}
```

---

## FastAPI Backend

### Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase URL and Groq API key

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

With the server running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/metrics` | Ingest metrics from agent |
| GET | `/api/metrics/latest` | Latest metric snapshot |
| GET | `/api/metrics/history` | Historical time-series |
| GET | `/api/anomalies` | Recent anomalies |
| GET | `/api/incidents` | Incident list |
| GET | `/api/incidents/{id}` | Incident detail |
| POST | `/api/incidents/{id}/analyze` | Trigger AI analysis |
| GET | `/api/dashboard/summary` | Dashboard overview |
| GET | `/api/dashboard/timeseries` | Chart data |
| GET | `/api/system/status` | System health |

---

## Supabase PostgreSQL

The backend uses PostgreSQL hosted on Supabase. To connect:

1. Create a Supabase project at https://supabase.com
2. Find your database connection string in Settings → Database
3. Set `DATABASE_URL` in `backend/.env`

```bash
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.PROJECTREF.supabase.co:5432/postgres
```

---

## Anomaly Detection

Detection is **entirely deterministic** — no LLM involvement.

### Thresholds

| Metric | Warning | Critical |
|---|---|---|
| CPU Usage | ≥ 70% | ≥ 90% |
| Memory Usage | ≥ 75% | ≥ 90% |
| Disk Usage | ≥ 80% | ≥ 90% |
| System Load | > cpu_count | > 2 × cpu_count |
| Response Time | > 2000ms | > 5000ms |

All thresholds configurable via environment variables.

### Persistence Detection

A single spike does not create an incident. The anomaly must persist for `ANOMALY_CONSECUTIVE_SAMPLES` (default: 3) consecutive observations before being marked as persistent.

---

## Incident Correlation

The correlation engine groups anomalies within `CORRELATION_WINDOW_MINUTES` (default: 5) into a single incident.

### Correlation Score Weights

| Metric | Weight |
|---|---|
| CPU Usage | +2 |
| Memory Usage | +2 |
| System Load | +2 |
| Response Time | +2 |
| Disk Usage | +1 |
| Persistent anomaly | +1 bonus |

### Deduplication

Every incident gets a deterministic `incident_key`:
```
SHA-256(hostname + sorted(affected_metric_names))[:32]
```

If an active incident with the same key exists, it is **updated** rather than creating a new one. This prevents alert storms from the same ongoing condition.

---

## LangGraph Workflow

```
START → collect_context → correlate → determine_severity
     → determine_cause → recommend_action → generate_summary → END
```

| Node | Responsibility |
|---|---|
| `collect_context` | Validate input data completeness |
| `correlate` | Build evidence list from anomalies and metric trends |
| `determine_severity` | Assess severity from anomaly severities and score |
| `determine_cause` | Call Groq LLM; fall back to rules if unavailable |
| `recommend_action` | Populate actions from LLM or rule-based logic |
| `generate_summary` | Compose final reasoning narrative |

---

## Groq Integration

Configure in `backend/.env`:

```bash
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

The LLM receives structured evidence (not raw logs or entire database dumps) and returns validated JSON:

```json
{
  "severity": "CRITICAL",
  "affected_metrics": ["CPU", "Memory", "System Load", "Response Time"],
  "probable_cause": "The instance is likely experiencing resource saturation...",
  "evidence": [
    "CPU remained above 90% for multiple consecutive observations",
    "Memory exceeded 90%",
    "Load increased alongside CPU usage"
  ],
  "recommended_actions": [
    "Inspect top CPU and memory consuming processes",
    "Review application logs for errors"
  ],
  "confidence": 0.9,
  "reasoning_summary": "CPU, memory, load, and response-time anomalies..."
}
```

**LLM Failure Handling:**
1. Retry twice on transient errors (connection, rate limit)
2. Validate output with Pydantic
3. Fall back to deterministic rule-based analysis
4. Incident is **always** created — monitoring never depends on LLM availability

---

## Frontend

### Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000 (or your backend URL)

# Start development server
npm run dev
```

Open http://localhost:5173

### Pages

- **Dashboard** — Live status banner, metric cards, trend charts, recent incidents
- **Metrics** — Historical charts with 15m/1h/6h/24h range selection
- **Incidents** — Filterable incident table
- **Incident Detail** — Full analysis with observed facts, evidence, AI reasoning, recommended actions

The UI clearly separates **"Observed data"** from **"Analysis"** to prevent confusing facts with inference.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — |
| `GROQ_API_KEY` | Groq API key | — |
| `GROQ_MODEL` | Groq model name | `llama-3.3-70b-versatile` |
| `MONITORING_AGENT_API_KEY` | Shared secret for agent auth | — |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |
| `CPU_WARNING_THRESHOLD` | CPU warning threshold % | `70` |
| `CPU_CRITICAL_THRESHOLD` | CPU critical threshold % | `90` |
| `MEMORY_WARNING_THRESHOLD` | Memory warning % | `75` |
| `MEMORY_CRITICAL_THRESHOLD` | Memory critical % | `90` |
| `DISK_WARNING_THRESHOLD` | Disk warning % | `80` |
| `DISK_CRITICAL_THRESHOLD` | Disk critical % | `90` |
| `ANOMALY_CONSECUTIVE_SAMPLES` | Samples before persistent anomaly | `3` |
| `CORRELATION_WINDOW_MINUTES` | Correlation time window | `5` |

### Agent (`agent/.env`)

| Variable | Description | Default |
|---|---|---|
| `BACKEND_URL` | FastAPI backend URL | `http://localhost:8000` |
| `MONITORING_AGENT_API_KEY` | Must match backend key | — |
| `COLLECTION_INTERVAL_SECONDS` | Metric collection interval | `30` |
| `MONITORED_URL` | Optional URL to measure response time | — |
| `MAX_RETRIES` | HTTP delivery retry attempts | `3` |

---

## Database Migrations

```bash
# Create a new migration (after model changes)
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

---

## Testing

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest app/tests/test_anomaly_detector.py -v

# Run specific test scenario
pytest app/tests/test_anomaly_detector.py::TestResourceSaturation -v
```

### Test Scenarios

| Scenario | Expected |
|---|---|
| Normal (CPU 30%, MEM 40%, DISK 45%) | No anomalies |
| CPU spike (CPU 95%) | CRITICAL CPU anomaly |
| Memory pressure (MEM 95%) | CRITICAL memory anomaly |
| Resource saturation (CPU 95%, MEM 92%, Load high) | ONE CRITICAL correlated incident |
| Disk pressure (DISK 94%) | CRITICAL disk anomaly |
| Continuing incident (3+ cycles) | Single incident updated |
| LLM unavailable | Rule-based fallback analysis |

---

## Demo Scenario

The system is designed to demonstrate this exact scenario:

**At 10:00 AM:**
```
CPU: 92%  Memory: 88%  Disk: 85%  Load: High
```

**At 10:05 AM:**
```
CPU: 96%  Memory: 91%  Load: Very High  Response Time: Increased
```

**Expected output:**
```
Severity: CRITICAL
Affected Metrics: CPU, Memory, Disk, System Load, Response Time

Probable Cause: The EC2 instance is likely experiencing resource saturation,
potentially caused by a high-resource process or increased application workload.

Evidence:
  - CPU remained above 90% for multiple consecutive observations
  - Memory exceeded 90% and is critically low
  - System load increased alongside CPU usage
  - Response time degraded during the same period

Recommended Actions:
  1. Inspect top CPU and memory consuming processes
  2. Review application and system logs
  3. Identify the workload responsible for resource consumption
  4. Consider workload optimization or EC2 scaling
```

The key behaviour: **ONE incident** is created and updated, not five separate CPU/Memory/Disk/Load/ResponseTime incidents.

---

## Future Improvements

- **AWS CloudWatch integration** — ingest CloudWatch metrics alongside psutil
- **Prometheus/Grafana** — standard metrics export endpoint
- **WebSocket streaming** — real-time dashboard updates without polling
- **Statistical baselines** — dynamic thresholds based on historical percentiles
- **ML anomaly detection** — Isolation Forest or time-series models for subtle anomalies
- **Multiple EC2 instances** — fleet-wide monitoring and cross-host correlation
- **Alerting** — Email/Slack/PagerDuty notifications on incident creation
- **Incident acknowledgement** — UI for engineers to acknowledge and track
- **Authentication/RBAC** — user accounts and role-based access control
- **Auto-remediation** — runbook execution on known incident patterns

---

## Design Decisions

**Why deterministic detection, not LLM detection?**
Threshold-based detection is fast, explainable, configurable, and works without internet access. The LLM's value is in *explaining* already-detected anomalies — not in determining whether CPU is high.

**Why correlation before AI analysis?**
Correlating first means the LLM receives a single, coherent set of evidence rather than being called repeatedly for each individual metric alert. This reduces cost, latency, and API calls.

**Why LangGraph instead of a single LLM call?**
LangGraph allows each step to be tested, replaced, or enhanced independently. The severity assessment node can apply deterministic rules before the LLM is called. The summary node can produce a fallback if the LLM fails. This is far more robust than one monolithic prompt.

**Why Supabase PostgreSQL?**
Standard PostgreSQL with zero additional complexity. Supabase adds a managed database UI and real-time capabilities that are useful for future extensions. The code is completely database-agnostic within SQLAlchemy.
