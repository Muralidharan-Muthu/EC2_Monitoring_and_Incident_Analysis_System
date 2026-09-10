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

### System Architecture Diagram

```mermaid
graph TD
    subgraph Client ["Frontend Layer (Browser)"]
        UI["React 18 + Vite + TypeScript Dashboard"]
        Charts["Recharts Metric Trends (Spline Gradients)"]
        IncidentView["Executive Incident Detail & Action Center"]
        UI --> Charts
        UI --> IncidentView
    end

    subgraph BackendServer ["Backend Monitoring Server (FastAPI)"]
        API["FastAPI REST Endpoints (/api/...)"]
        
        subgraph Ingestion ["Telemetry Ingestion & Quality"]
            SSHClient["AsyncSSH Client (Session Reused)"]
            Collectors["Linux Collectors: CPU, RAM, Disk, Load, Procs, Logs"]
            Normalizer["Strict Null-Safe Normalizer (No Fake Zeros)"]
            SSHClient --> Collectors --> Normalizer
        end

        subgraph DetectionEngine ["Deterministic Intelligence Engine"]
            AnomalyDetector["Anomaly Detector (Warning & Critical Thresholds)"]
            PersistenceTracker["Persistence Filter (N=3 Consecutive Samples)"]
            CorrelationEngine["Incident Correlation Engine (5-Min Window)"]
            Normalizer --> AnomalyDetector --> PersistenceTracker --> CorrelationEngine
        end

        subgraph AIWorkflow ["8-Node LangGraph Workflow"]
            LG1["1. Context Collection"] --> LG2["2. Evidence Validation"]
            LG2 --> LG3["3. Event Correlation"]
            LG3 --> LG4["4. Severity Assessment"]
            LG4 --> LG5["5. Probable Cause (Groq / Rule Fallback)"]
            LG5 --> LG6["6. Remediation Actions"]
            LG6 --> LG7["7. Executive Narrative"]
            LG7 --> LG8["8. Schema Validation"]
        end

        CorrelationEngine -->|"Multi-Metric Incident"| LG1
    end

    subgraph TargetHost ["Monitored Infrastructure (AWS EC2)"]
        EC2["Ubuntu 24.04 / 22.04 LTS (2 vCPU, EBS Root)"]
        ProcFS["/proc/stat, /proc/loadavg, /proc/net/dev"]
        SysTools["mpstat, free -m, df -P /, ps, journalctl"]
        EC2 --> ProcFS
        EC2 --> SysTools
    end

    subgraph Persistence ["Storage & AI Services"]
        Supabase[("Supabase PostgreSQL (Schema: ec2_monitoring_working)")]
        Groq["Groq Cloud LLM (qwen/qwen3.8-27b)"]
    end

    UI <-->|"HTTP REST (JSON)"| API
    API --> Ingestion
    Normalizer --> Supabase
    CorrelationEngine --> Supabase
    SSHClient <-->|"SSH (Port 22, Key Auth)"| EC2
    LG5 <-->|"JSON API"| Groq
```

The system enforces a strict unidirectional security boundary:
- The React frontend **NEVER** communicates directly with EC2 and does not store SSH keys.
- The private `.pem` key stays secured on the backend and is excluded from source control.

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

## 17. Explanation of Approach: Anomaly Detection

The system uses a **multi-layered deterministic anomaly detection pipeline** designed specifically to avoid alert fatigue, false positives, and silent failures in cloud infrastructure:

### 1. Agentless Telemetry Collection via Safe Linux Tools
- Instead of requiring heavyweight daemon agents, the system securely executes lightweight POSIX-standard diagnostic tools (`mpstat`, `free -m`, `df -P /`, `cat /proc/loadavg`, `ps -eo ...`, `journalctl`) over a persistent SSH channel.
- Each collector operates independently: a temporary failure in one command never blocks or corrupts other collectors.

### 2. Strict Null Safety (No Fabricated Data)
- In cloud systems, a failed metric collection (e.g. timeout or network hiccup) is **fundamentally different** from a healthy metric (`0%`).
- If a collection fails or produces unparseable data, it is recorded and presented strictly as `null` (`"-"` in the UI).
- The anomaly engine explicitly ignores `null` values without assuming normalcy, ensuring true zero-fabrication integrity.

### 3. Configurable Multi-Tier Thresholds
Metrics are evaluated against two deterministic thresholds:
| Monitored Subsystem | Metric Key | Warning Threshold | Critical Threshold | Baseline Rationale |
|---|---|---|---|---|
| **CPU Saturation** | `cpu_usage` | `> 70.0%` | `> 90.0%` | High sustained CPU starves kernel interrupts and context switching. |
| **Physical Memory** | `memory_usage` | `> 75.0%` | `> 90.0%` | Linux buffers/cache are treated as reclaimable; triggers when available RAM is depleted. |
| **Root Disk Storage** | `disk_usage` | `> 80.0%` | `> 85.0% / 90.0%` | Prevents disk full lockups on the root partition (`/dev/root`). |
| **System Load** | `load_1m` | `> Cores × 1.5` | `> Cores × 2.0` | Dynamically scaled to `nproc` (e.g. Load > 4.0 on a 2-core EC2 machine). |
| **HTTP Latency** | `response_time_ms`| `> 1000 ms` | `> 2000 ms` | Detects user-facing degradation during backend compute starvation. |

### 4. Sliding Persistence Filter (Anti-Flapping)
- Single-sample spikes (such as a cron job or brief package update) are common on Linux servers and should not wake up on-call engineers.
- An anomaly is marked as persistent only when it breaches thresholds across `ANOMALY_CONSECUTIVE_SAMPLES = 3` consecutive collection cycles (~60–90 seconds).

---

## 18. Explanation of Approach: Incident Correlation & Analysis

### The Problem: Alert Storming & Disjointed Notifications
During real-world outages (e.g., memory exhaustion or CPU starvation), multiple symptoms trigger simultaneously:
- A CPU spike causes processes to queue up, driving **System Load** to 4.8.
- Worker threads starve, causing application **Response Time** to surge from 120ms to 2,500ms.
- High memory pressure leads to disk paging and cache eviction.
Traditional monitoring systems emit 4 or 5 separate alerts: one for CPU, one for RAM, one for Load, and one for Latency. On-call engineers are flooded with disjointed alerts without understanding the root cause.

### The Solution: Temporal & Semantic Incident Correlation
Our system correlates related events into **one unified incident**:

1. **Sliding Temporal Window (`CORRELATION_WINDOW_MINUTES = 5`)**:
   - Anomalies detected within a 5-minute sliding window on the same host are automatically evaluated for causal relationships.
2. **Deduplication Key (`hostname + incident_family`)**:
   - Creates a deterministic grouping key (e.g., `ip-172-31-3-102:resource_saturation`).
   - If subsequent metrics breach thresholds 2 minutes later (e.g., Response Time spikes after CPU saturation), they are **appended to the existing incident** rather than spawning new duplicate incidents.
3. **Composite Severity & Impact Scoring**:
   - Evaluates multi-metric saturation:
     - `CRITICAL`: Multiple interdependent subsystems saturated simultaneously (e.g. CPU + RAM + Disk).
     - `HIGH`: Sustained critical breach of a single major resource.
     - `MEDIUM`: Multiple warning-level anomalies.
     - `LOW`: Isolated warning anomaly.
4. **8-Node LangGraph AI Workflow with Groq (`qwen/qwen3.8-27b`)**:
   - Executes an 8-node sequential StateGraph:
     `Context -> Evidence -> Correlation -> Severity -> Probable Cause -> Recommendations -> Narrative -> Pydantic Validation`.
   - Distinguishes observed facts from AI inference.
   - Identifies specific culprit processes from `ps` evidence (e.g. `stress-ng-cpu consuming 94.3% CPU`).
5. **Deterministic Rule Engine Fallback**:
   - If Groq is unavailable, network is unreachable, or API quotas are exhausted, the system automatically switches to deterministic rule-based diagnosis. Monitoring and alerting **never fail**.

---

## 19. Technical Assessment Scenario Walkthrough

The system was evaluated against the exact operational progression specified in the technical assessment:

```
[10:00 AM] Initial Saturation:
  ● CPU Usage: 92% (CRITICAL)
  ● Memory Usage: 88% (WARNING)
  ● Disk Usage: 85% (WARNING)
  ● System Load: High (3.5)
  ↳ System Action: Anomaly detector flags 4 breaches. Correlation engine binds them 
    into ONE incident (INC-1). No separate alerts created.

[10:05 AM] Escalating Impact (5 minutes later):
  ● CPU Usage: 96% (CRITICAL)
  ● Memory Usage: 91% (CRITICAL)
  ● Response Time: Increased to 2,500ms (CRITICAL)
  ● System Load: Very High (4.8)
  ↳ System Action: Recognized as the continuation of the existing incident. 
    Incident INC-1 is updated with new metrics, elevated to CRITICAL severity, 
    and AI root cause analysis diagnoses cascading host starvation caused by worker thread contention.
```

---

## 20. LangGraph Workflow Structure

The sequential 8-node LangGraph pipeline executes:
```
START
  ↓
[1] Collect Incident Context   (app/ai/nodes/context.py)
  ↓
[2] Validate Evidence          (app/ai/nodes/evidence.py)
  ↓
[3] Correlate Related Events   (app/ai/nodes/correlation.py)
  ↓
[4] Assess Severity            (app/ai/nodes/severity.py)
  ↓
[5] Determine Probable Cause   (app/ai/nodes/root_cause.py)  <--- Groq LLM / Rule Fallback
  ↓
[6] Generate Recommendations   (app/ai/nodes/recommendation.py)
  ↓
[7] Generate Incident Summary  (app/ai/nodes/summary.py)
  ↓
[8] Validate Structured Output (app/ai/nodes/validation.py)  <--- Pydantic Schema Validation
  ↓
END
```

---

## 21. Automated Testing

The comprehensive test suite covers 49 automated test cases across all critical subsystems:
```bash
cd backend
.\venv\Scripts\python.exe -m pytest app/tests/ -v
```

### Verified Test Categories:
- **Remote SSH & Collectors**: `mpstat`, `free -m`, `df -P /`, `loadavg`, `ps`, `journalctl`.
- **Strict Null Safety**: Unmeasured metrics return `null`, never `0%`.
- **Anomaly Detection**: Warnings, criticals, consecutive persistence, and null skipping.
- **Incident Correlation**: Multi-anomaly grouping, temporal window, deduplication key.
- **Assessment Scenario**: Exact 10:00 AM -> 10:05 AM cascade evaluation.
- **LangGraph & Groq**: 8-node pipeline, JSON schema compliance, deterministic fallback.

---

## 22. Stress Testing & Demonstration Suite

An automated interactive CLI suite is provided to trigger realistic incidents on your AWS EC2 instance:

### Running from Windows:
```cmd
.\stress.bat
```

### Running from Linux / Git Bash:
```bash
./stress_ec2.sh
```

### Available Stress Scenarios:
| Option | Scenario | Description | Target Impact |
|---|---|---|---|
| **`[1 / A]`** | **Scenario A: CPU Saturation** | 2 cores pinned at 97% load | Flags `CPU_CRITICAL (>90%)` |
| **`[2 / B]`** | **Scenario B: RAM Saturation** | Drops cache & allocates 95% RAM | Flags `MEMORY_CRITICAL (>90%)` |
| **`[3 / C]`** | **Scenario C: Root Disk Saturation** | Allocates 13.3 GB in `/var/tmp` on `/dev/root` | Flags `DISK_CRITICAL (>90%)` |
| **`[4 / D]`** | **Scenario D: Assessment Multi-Resource** | CPU 96% + RAM 91% concurrently | Single Correlated Incident + LangGraph AI |
| **`[5 / E]`** | **Scenario E: Extreme Triple Saturation** | CPU + RAM + Root Disk simultaneously | All 3 subsystems saturated concurrently |
| **`[6 / K]`** | **Stop All / Clean** | Kills `stress-ng` & removes temporary disk files | Restores free space & healthy baseline |

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
