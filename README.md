# EC2 Monitoring and Incident Analysis System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791.svg?logo=postgresql&logoColor=white)](https://supabase.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-qwen3.8--27b-F55036.svg)](https://groq.com)
[![AsyncSSH](https://img.shields.io/badge/AsyncSSH-Remote_Monitoring-blue.svg)](https://asyncssh.readthedocs.io)

An agentless, production-grade cloud infrastructure monitoring and incident analysis platform. The backend connects securely to a remote AWS EC2 Linux instance over **SSH**, executes safe native Linux telemetry commands, parses performance metrics, deterministically detects abnormal behavior with persistence tracking, correlates related multi-metric abnormalities into unified incidents, and produces structured incident root cause analysis using an **8-node LangGraph workflow powered by Groq (`qwen/qwen3.8-27b`)** with resilient deterministic fallback.

---

## Architecture Diagram

![System Architecture](docs/architecture.png)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Assessment Requirements Mapping](#2-assessment-requirements-mapping)
3. [Architecture](#3-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Project Structure](#5-project-structure)
6. [SSH Monitoring Architecture](#6-ssh-monitoring-architecture)
7. [Linux Commands Explained](#7-linux-commands-explained)
8. [Environment Variables](#8-environment-variables)
9. [Supabase Configuration](#9-supabase-configuration)
10. [Groq Configuration](#10-groq-configuration)
11. [Backend Setup](#11-backend-setup)
12. [Frontend Setup](#12-frontend-setup)
13. [SSH Key Configuration](#13-ssh-key-configuration)
14. [Running the System](#14-running-the-system)
15. [API Documentation](#15-api-documentation)
16. [Monitoring Process](#16-monitoring-process)
17. [Anomaly Detection](#17-anomaly-detection)
18. [Incident Correlation](#18-incident-correlation)
19. [LangGraph Workflow](#19-langgraph-workflow)
20. [Groq Analysis](#20-groq-analysis)
21. [Testing](#21-testing)
22. [Stress Testing](#22-stress-testing)
23. [Example Incident Scenario](#23-example-incident-scenario)
24. [Troubleshooting](#24-troubleshooting)
25. [Security Considerations](#25-security-considerations)
26. [Future Improvements](#26-future-improvements)

---

## 1. Project Overview

Modern cloud infrastructure monitoring often forces teams to choose between complex, heavyweight agent deployments (like Datadog or Prometheus node-exporter) and fragile cloud-provider integrations. 

The **EC2 Monitoring and Incident Analysis System** solves this by implementing **agentless remote monitoring**:
- The monitoring backend securely SSHes into the remote EC2 instance on a configurable schedule (default every 30 seconds) or on-demand.
- Native Linux `/proc` and system commands collect raw metrics.
- **Strict Null Safety Rule**: If a command or metric fails, it is stored and reported as `null` (`"-"` in UI). The system **NEVER** fabricates fake default values like `CPU=0%` or `Memory=0%`.
- Deterministic rules detect anomalies and track persistence across consecutive samples.
- A correlation engine groups multi-metric symptoms (e.g. CPU + Memory + System Load) into **one** unified incident with deduplication.
- An 8-node LangGraph pipeline enhances the incident with structured root cause analysis and remediation commands via Groq LLM, while guaranteeing complete deterministic rule fallback if the LLM is unavailable.

---

## 2. Assessment Requirements Mapping

| Requirement | Description | Implementation in Codebase |
|---|---|---|
| **Requirement 1: AWS EC2 Launch / Configuration** | Target remote Linux instance on AWS EC2 Ubuntu | Configured via environment variables (`EC2_HOST`, `EC2_PORT`, `EC2_USERNAME`, `EC2_PRIVATE_KEY_PATH`). Zero hardcoding. Verified live against `ubuntu@ec2-3-110-104-207.ap-south-1.compute.amazonaws.com`. |
| **Requirement 2: Linux Commands / Tools** | Remote execution of standard Linux diagnostic commands | Modular collectors in `backend/app/collectors/` using `mpstat`, `nproc`, `free -m`, `df -P /`, `cat /proc/loadavg`, `ps -eo ...`, `cat /proc/net/dev`, `journalctl -p warning..err`, and `uname -r`. |
| **Requirement 3: Python Application / Script** | Backend server, database persistence, and schedulers | FastAPI async application, SQLAlchemy 2.0 with asyncpg, Alembic migrations to Supabase PostgreSQL, AsyncSSH client session reuse. |
| **Requirement 4: Abnormal Behavior Detection** | Deterministic thresholding and persistence tracking | `backend/app/anomaly/rules.py` and `persistence.py`. Skips `null` metrics without assuming normal. Requires N=3 consecutive samples for persistence. |
| **Requirement 5: Correlated Incident Analysis** | Multi-anomaly grouping into a single incident | `backend/app/incidents/correlation.py` and `incident_service.py`. Sliding 5-minute temporal window and semantic family grouping. Prevents duplicate incidents. |
| **Requirement 6: Severity, Causes, and Recommendations** | 4-tier severity, probable cause, actionable actions | Explicit severity calculation (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), 8-node LangGraph pipeline in `backend/app/ai/nodes/`, Groq LLM integration with deterministic fallback. |

---

## 3. Architecture

The system follows a strict unidirectional security boundary:
```
React Dashboard (Vite)
        ↓ HTTP REST (/api/...)
FastAPI Backend
        ↓ SSH (:22) with Private Key
AWS EC2 Ubuntu Host (Linux Commands)
```

The React frontend **NEVER** communicates directly with EC2 or holds SSH keys. The private `.pem` key remains strictly on the FastAPI server and is excluded from source control.

---

## 4. Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), AsyncSSH, Structlog, Tenacity, Alembic.
- **Frontend**: React 18, Vite, TypeScript, Recharts, Axios, Vanilla CSS design system.
- **Database**: PostgreSQL on Supabase (`db.zgohttvynajravzciame.supabase.co:5432`, schema `ec2_monitoring_working`).
- **AI / Agentic**: LangGraph (8-node StateGraph), Groq Python SDK, model `qwen/qwen3.8-27b`.
- **Operating System**: Linux (Ubuntu 22.04 / 24.04 / 26.04) on AWS EC2.

---

## 5. Project Structure

```
EC2_Monitoring/
├── backend/
│   ├── app/
│   │   ├── ai/                      # 8-node LangGraph + Groq pipeline
│   │   │   ├── nodes/               # context, evidence, correlation, severity, root_cause, recommendation, summary, validation
│   │   │   ├── graph.py             # Compiled LangGraph StateGraph
│   │   │   ├── groq_client.py       # Groq API client with retry logic
│   │   │   ├── prompts.py           # Structured prompts
│   │   │   └── state.py             # Strongly typed IncidentAnalysisState
│   │   ├── anomaly/                 # Deterministic anomaly detection
│   │   │   ├── detector.py          # Main anomaly orchestrator
│   │   │   ├── persistence.py       # Consecutive violation tracking
│   │   │   └── rules.py             # Threshold & trend rules (null-safe)
│   │   ├── api/routes/              # FastAPI endpoints
│   │   │   ├── health.py            # /api/health
│   │   │   ├── monitoring.py        # /api/monitoring (status, current, collect)
│   │   │   ├── metrics.py           # /api/metrics (latest, history)
│   │   │   ├── incidents.py         # /api/incidents (list, detail, analyze)
│   │   │   └── dashboard.py         # /api/dashboard/summary
│   │   ├── collectors/              # Remote SSH Linux collectors
│   │   │   ├── cpu.py               # mpstat 1 1, nproc, /proc/stat
│   │   │   ├── memory.py            # free -m
│   │   │   ├── disk.py              # df -P /
│   │   │   ├── load.py              # /proc/loadavg
│   │   │   ├── process.py           # ps top CPU/memory
│   │   │   ├── network.py           # /proc/net/dev
│   │   │   ├── logs.py              # journalctl
│   │   │   ├── response_time.py     # Optional HTTP probe
│   │   │   └── system.py            # hostname, uname, os-release
│   │   ├── core/                    # config, database, logging
│   │   ├── incidents/               # Correlation, severity, lifecycle
│   │   ├── models/                  # SQLAlchemy models
│   │   ├── monitoring/              # CollectorService, Normalizer, SnapshotService
│   │   ├── schemas/                 # Pydantic validation schemas
│   │   └── tests/                   # 59 automated pytest tests
│   ├── alembic/                     # Database migrations
│   ├── requirements.txt             # Backend dependencies
│   └── .env.example                 # Example configuration
├── frontend/
│   ├── src/
│   │   ├── components/              # MetricCard, MetricChart, StatusBadge, IncidentCard, IncidentTimeline, ProcessTable, LogPanel
│   │   ├── pages/                   # Dashboard, Metrics, Incidents, IncidentDetail
│   │   ├── services/                # api, monitoringApi, metricsApi, incidentsApi
│   │   └── utils/                   # format.ts (strict null handling)
│   ├── package.json
│   └── .env.example
├── docs/                            # architecture.md, architecture.png, incident-analysis.md
├── start.bat                        # Windows launcher
├── start.ps1                        # PowerShell launcher
├── start.sh                         # Linux/macOS launcher
└── README.md                        # Documentation
```

---

## 6. SSH Monitoring Architecture

The backend establishes an async SSH connection via `AsyncSSH` to the remote EC2 instance.

### Key Implementation Principles:
1. **Connection Reuse**: Executing 8 separate SSH handshakes per cycle adds 10+ seconds of overhead. `EC2SSHClient.session()` reuses a single authenticated session across all collectors in a cycle, finishing in **~1.5 seconds**.
2. **Strict Command Allowlist**: Only pre-approved diagnostic command templates are permitted. Frontend users cannot submit arbitrary shell commands.
3. **Graceful Degradation**: If an individual collector command fails (e.g. permission denied or missing binary), that specific metric returns `null`, while all other collectors succeed.

---

## 7. Linux Commands Explained

| Metric / Domain | Linux Command | Technical Rationale |
|---|---|---|
| **CPU Utilization** | `mpstat 1 1` | Provides high-precision, instantaneous CPU %idle across 1-second sample without historical skew. |
| **CPU Core Count** | `nproc` | Measures active CPU processing cores; baseline for system load threshold calculations. |
| **Memory Breakdown** | `free -m` | Provides accurate RAM stats in MB. Usage calculated via `((total - available) / total) * 100` to properly treat disk caches/buffers as reclaimable. |
| **Disk Storage** | `df -P /` | Uses POSIX portable output format to prevent line-wrapping on long mount strings. |
| **System Load** | `cat /proc/loadavg` | Native kernel interface reporting 1-minute, 5-minute, and 15-minute runnable and uninterruptible queue depths. |
| **Processes** | `ps -eo pid,comm,%cpu,%mem --sort=-%cpu \| head -n 11` | Collects top CPU and memory consumers with PID and process names for forensic evidence. |
| **Network I/O** | `cat /proc/net/dev` | Aggregates bytes received and transmitted across all physical network adapters (skips loopback `lo`). |
| **System Logs** | `journalctl -p warning..err -n 20 --no-pager` | Focuses on active kernel and service warnings/errors without reading unbounded logs. |
| **Host Information** | `hostname`, `uname -r`, `cat /etc/os-release` | Verifies OS distribution, AWS kernel version, and instance identifier. |

---

## 8. Environment Variables

Create `backend/.env` based on `backend/.env.example`:

```env
APP_ENV=development
DEBUG=false
LOG_LEVEL=INFO

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.zgohttvynajravzciame.supabase.co:5432/postgres

# Remote EC2 SSH Configuration
EC2_HOST=ec2-3-110-104-207.ap-south-1.compute.amazonaws.com
EC2_PORT=22
EC2_USERNAME=ubuntu
EC2_PRIVATE_KEY_PATH=ec2-monitoring-key.pem
SSH_CONNECT_TIMEOUT_SECONDS=10
SSH_COMMAND_TIMEOUT_SECONDS=15

# Background Collection Schedule
COLLECTION_INTERVAL_SECONDS=30

# Deterministic Thresholds
CPU_WARNING_THRESHOLD=70
CPU_CRITICAL_THRESHOLD=90
MEMORY_WARNING_THRESHOLD=75
MEMORY_CRITICAL_THRESHOLD=90
DISK_WARNING_THRESHOLD=80
DISK_CRITICAL_THRESHOLD=90
CORRELATION_WINDOW_MINUTES=5
ANOMALY_CONSECUTIVE_SAMPLES=3

# Groq LLM Configuration
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.8-27b

# Optional HTTP App Response Time
MONITORED_URL=
RESPONSE_TIME_WARNING_MS=1000
RESPONSE_TIME_CRITICAL_MS=2000

CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 9. Supabase Configuration

1. Use direct connection URI `db.zgohttvynajravzciame.supabase.co:5432` with user `postgres`.
2. Target schema: `ec2_monitoring_working`.
3. Run migrations:
```bash
cd backend
python -m alembic upgrade head
```

---

## 10. Groq Configuration

- Tested and benchmarked model: `qwen/qwen3.8-27b`.
- Operates in strict JSON object mode (`response_format={"type": "json_object"}`).
- Low temperature (`0.1`) ensures deterministic and reproducible reasoning.
- If `GROQ_API_KEY` is omitted or invalid, the backend automatically switches to `rule_engine` mode with zero impact on monitoring.

---

## 11. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 12. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit: `http://localhost:5173`

---

## 13. SSH Key Configuration

1. Place your private `.pem` key file on the server running FastAPI (e.g. `ec2-monitoring-key.pem` in project root).
2. Set `EC2_PRIVATE_KEY_PATH=ec2-monitoring-key.pem` in `backend/.env`.
3. Ensure file permissions (on Linux: `chmod 400 ec2-monitoring-key.pem`).
4. **NEVER commit the `.pem` file to Git** (enforced in `.gitignore`).

---

## 14. Running the System

Use the convenient one-command startup scripts:

### Windows:
```cmd
start.bat all
```
or PowerShell:
```powershell
.\start.ps1 all
```

### Linux / macOS:
```bash
chmod +x start.sh
./start.sh all
```

---

## 15. API Documentation

Swagger UI is available at `http://localhost:8000/docs`.

### Core Endpoints:
- `GET /api/monitoring/status`: Checks EC2 reachability over SSH.
- `GET /api/monitoring/current`: Triggers live SSH collection, evaluates anomalies, saves snapshot, returns data.
- `POST /api/monitoring/collect`: Explicitly triggers one collection cycle.
- `GET /api/metrics/latest`: Returns latest persisted metric snapshot.
- `GET /api/metrics/history?range=1h`: Returns time-series data for charts (`15m`, `1h`, `6h`, `24h`).
- `GET /api/incidents`: Lists active and historical incidents.
- `GET /api/incidents/{id}`: Returns incident detail with evidence and analysis.
- `POST /api/incidents/{id}/analyze`: Runs the 8-node LangGraph analysis workflow on demand.
- `GET /api/dashboard/summary`: Summary metrics, SSH connectivity, active incident count.

---

## 16. Monitoring Process

Every collection cycle (background or manual):
1. Authenticates to EC2 via AsyncSSH.
2. Runs collectors in parallel within the session.
3. Normalizes metrics into a `UnifiedSnapshot` with Data Quality calculation.
4. Persists `MetricSnapshot` and `ProcessSnapshot` to Supabase.
5. Runs deterministic anomaly detector.
6. Evaluates persistence across samples.
7. Groups active anomalies into correlated incidents.
8. If an incident requires analysis, invokes LangGraph with Groq.

---

## 17. Anomaly Detection

- Evaluates CPU, Memory, Disk, System Load, and Response Time against warning and critical thresholds.
- **Strict Rule**: When a metric is `null`, anomaly evaluation is skipped. It is **never** assumed to be normal.
- **Persistence**: Requires `ANOMALY_CONSECUTIVE_SAMPLES` (3) before marking an anomaly as persistent high.
- **Trend Detection**: Flags deteriorating patterns (e.g. rising CPU across consecutive observations).

---

## 18. Incident Correlation

When multiple anomalies occur concurrently within `CORRELATION_WINDOW_MINUTES` (5 mins):
- They are grouped into **ONE** incident.
- Deduplication key derived from `hostname + family` prevents duplicate `INC-001`, `INC-002` spam.
- Severity levels: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- Auto-resolves after 10 minutes of healthy operating baselines.

---

## 19. LangGraph Workflow

The sequential 8-node LangGraph pipeline executes:
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
[5] Determine Probable Cause  (app/ai/nodes/root_cause.py)
  ↓
[6] Generate Recommendations  (app/ai/nodes/recommendation.py)
  ↓
[7] Generate Incident Summary (app/ai/nodes/summary.py)
  ↓
[8] Validate Structured Output(app/ai/nodes/validation.py)
  ↓
END
```

---

## 20. Groq Analysis

- Invoked during Node 5 (`determine_root_cause`) and Node 6 (`generate_recommendations`).
- Strict prompt instructions:
  1. Base analysis ONLY on supplied evidence.
  2. Never claim certainty; use "Likely", "Evidence suggests".
  3. Output valid JSON adhering to `LLMAnalysisOutput` schema.
- Automatic fallback: If Groq rate limits or fails, `analysis_source="rule_engine"` is activated.

---

## 21. Testing

The comprehensive test suite covers 59 automated test cases:
```bash
cd backend
.\venv\Scripts\python.exe -m pytest app/tests/ -v
```

### Verified Test Categories:
- SSH execution & failure handling.
- Collectors parsing: CPU, Memory, Disk, Load, Processes, Network, Logs.
- Strict null preservation: no fake zeros.
- Data quality states: COMPLETE, PARTIAL, FAILED.
- Anomaly persistence tracking and null skipping.
- Incident correlation and deduplication.
- 4-tier severity evaluation.
- Incident lifecycle & auto-resolution.
- LangGraph 8-node workflow with Groq fallback.
- FastAPI REST endpoints.

---

## 22. Stress Testing

For demonstration and testing purposes, you can generate simulated resource pressure on the EC2 machine:

```bash
# CPU Stress (2 cores for 120s)
stress-ng --cpu 2 --timeout 120s

# Memory Stress (80% of RAM for 120s)
stress-ng --vm 1 --vm-bytes 80% --timeout 120s

# Combined Resource Saturation
stress-ng --cpu 2 --vm 1 --vm-bytes 70% --timeout 120s
```

*Note: Stress testing tools are for demonstration only and are not part of production monitoring.*

---

## 23. Example Incident Scenario

1. User or workload runs `stress-ng --cpu 2 --vm 1 --vm-bytes 80%`.
2. Backend monitoring cycle connects to EC2 via SSH.
3. Telemetry captured:
   - CPU: 96.2% (exceeds critical threshold 90%)
   - Memory: 91.5% (exceeds critical threshold 90%)
   - Load (1m): 4.10 (exceeds 2x core count = 4.0)
   - Top process: `stress-ng` (CPU: 94.0%, Mem: 45.0%)
4. Correlation Engine correlates all 3 anomalies into **ONE** `CRITICAL` incident.
5. LangGraph queries Groq (`qwen/qwen3.8-27b`).
6. AI analysis returns:
   - Probable cause: "Evidence suggests severe resource saturation likely caused by high-intensity stress testing process ('stress-ng') consuming available CPU cycles and memory allocations."
   - Recommended actions: `ps -eo pid,comm,%cpu --sort=-%cpu`, `free -m`, `journalctl -p warning..err`.
   - Confidence: 95%.
   - Source: `Groq LLM (qwen/qwen3.8-27b)`.

---

## 24. Troubleshooting

- **SSH Connection Timeout**: Verify EC2 Security Group inbound rule allows Port 22 from your backend IP.
- **Permission Denied (Publickey)**: Check `EC2_PRIVATE_KEY_PATH` points to the correct `.pem` key file and `EC2_USERNAME=ubuntu`.
- **Database Connection Error**: Verify `DATABASE_URL` credentials and that Supabase allows connections.
- **Frontend Shows "-" for Metrics**: This is the expected, correct behavior when a metric was not collected or failed. Check collector status via `GET /api/monitoring/current`.

---

## 25. Security Considerations

- **Server-Side Key Storage**: Private keys never leave the backend. Frontend has zero SSH access.
- **Command Allowlist**: Only pre-compiled diagnostic commands are run. No user-supplied shell input is executed.
- **Safe Error Messages**: Internal stack traces and database credentials are not exposed in API responses.
- **Git Protection**: `.gitignore` strictly blocks `*.pem`, `.env`, and secret keys.

---

## 26. Future Improvements

- Multi-host EC2 inventory monitoring.
- CloudWatch metric cross-correlation.
- Webhook notifications (Slack, PagerDuty).
- Automated remediation playbooks over SSH (with human-in-the-loop confirmation).
