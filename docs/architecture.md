# EC2 Monitoring and Incident Analysis System — Architecture

## 1. High-Level Architecture Overview

The EC2 Monitoring and Incident Analysis System operates as an **agentless, remote monitoring and incident analysis platform**. Unlike traditional monitoring systems that require permanently running daemon agents installed on monitored instances, this system connects remotely to the AWS EC2 instance over **SSH** from the FastAPI backend, executes native Linux commands, parses real telemetry, detects anomalies deterministically, correlates multi-metric saturation events, and performs multi-stage incident reasoning enhanced by an 8-node **LangGraph** workflow powered by **Groq (`qwen/qwen3.8-27b`)**.

```
React Frontend (Vite + TS)
        |
        | HTTP REST (/api/...)
        v
FastAPI Backend
        |
        +--- AsyncSSH (Server-side private key authentication)
        |       |
        |       v
        |    AWS EC2 Ubuntu Instance
        |    +-----------------------------------------------+
        |    | Safe Linux Telemetry Commands                 |
        |    | - CPU: mpstat 1 1, nproc, /proc/stat          |
        |    | - Memory: free -m                             |
        |    | - Disk: df -P /                               |
        |    | - Load: cat /proc/loadavg                     |
        |    | - Processes: ps -eo pid,comm,%cpu,%mem        |
        |    | - Network: cat /proc/net/dev                  |
        |    | - Logs: journalctl -p warning..err -n 20      |
        |    | - System: hostname, uname -r, /etc/os-release |
        |    +-----------------------------------------------+
        |
        +---> PostgreSQL (Supabase schema: ec2_monitoring_working)
        |
        +---> Metric Normalizer & Strict Null Safety (No fake zeros)
        |
        +---> Deterministic Anomaly Detector (Warning & Critical thresholds)
        |
        +---> Anomaly Persistence Tracker (Consecutive violations filter)
        |
        +---> Incident Correlation Engine (Temporal + Semantic correlation)
        |
        +---> Incident Lifecycle Manager (OPEN -> INVESTIGATING -> RESOLVED)
        |
        +---> 8-Node LangGraph Pipeline
        |       |
        |       v
        |    Groq LLM (qwen/qwen3.8-27b) [With Rule Engine Fallback]
        |
        v
Structured Incident Analysis & UI Telemetry
```

---

## 2. Component Breakdown

### 2.1 SSH Client & Execution Engine (`app/ssh/`)
- **Library**: `asyncssh` for non-blocking asynchronous SSH connections matching FastAPI's async event loop.
- **Connection Reuse**: During a single collection cycle, a single authenticated SSH session is opened via `async with client.session() as session:`. All 8 collectors execute within this session, reducing round-trip latency from ~12s down to ~1.5s.
- **Command Allowlist**: Strict command allowlist validation in `app/ssh/executor.py` prevents arbitrary command injection or dangerous tokens (`rm`, `reboot`, `sudo`, `curl`, pipes to bash).
- **Result Structure**: All command results return `CommandResult` containing stdout, stderr, exit code, execution duration, and success flag.

### 2.2 Remote Linux Telemetry Collectors (`app/collectors/`)
Each collector operates independently and adheres to the **Strict Nullability Rule**:
1. **CPU Collector (`cpu.py`)**: Executes `mpstat 1 1` for instantaneous CPU utilization and `nproc` for cores. Falls back to `/proc/stat`. On failure, returns `cpu_usage: null` (never `0.0`).
2. **Memory Collector (`memory.py`)**: Executes `free -m`. Computes percentage as `((total - available) / total) * 100`. Returns MB breakdown.
3. **Disk Collector (`disk.py`)**: Executes `df -P /` using standard POSIX block sizes. Returns usage % and GB totals.
4. **System Load Collector (`load.py`)**: Parses `/proc/loadavg` for 1m, 5m, and 15m load averages.
5. **Process Collector (`process.py`)**: Executes `ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 11` and `--sort=-%mem | head -n 11`. Merges and returns structured processes without fabricating data.
6. **Network Collector (`network.py`)**: Reads `/proc/net/dev`, sums received and transmitted bytes across non-loopback interfaces (eth0, ens5), ignoring `lo`.
7. **Log Collector (`logs.py`)**: Executes `journalctl -p warning..err -n 20 --no-pager`. Gracefully handles permission issues as `permission_denied` without assuming "no errors".
8. **System Info Collector (`system.py`)**: Gathers hostname, kernel version (`uname -r`), and OS release (`/etc/os-release`).
9. **Response Time Collector (`response_time.py`)**: Probes `MONITORED_URL` via HTTP. If unconfigured, marks monitor as `disabled` with `null` metrics without raising alerts.

### 2.3 Metric Normalization & Data Quality (`app/monitoring/`)
- Aggregates raw collector outputs into a `UnifiedSnapshot`.
- Calculates Data Quality:
  - `COMPLETE`: All critical collectors succeeded.
  - `PARTIAL`: Some collectors succeeded, some failed.
  - `FAILED`: Connection could not be established.
- Strictly preserves `null` for unmeasured data across database, schemas, and API.

### 2.4 Anomaly Detection & Persistence (`app/anomaly/`)
- Deterministic rules compare actual measured metrics against configurable thresholds.
- **Null Safety**: If `cpu_usage is null`, evaluation is skipped. It is **NOT** classified as normal.
- **Persistence Tracking**: Transient spikes do not trigger critical alerts. Requires `ANOMALY_CONSECUTIVE_SAMPLES` (default 3) before flagging as persistent.
- **Trend Detection**: Flags deteriorating trends (e.g. 80% -> 85% -> 90% -> 95%).

### 2.5 Incident Correlation & Lifecycle (`app/incidents/`)
- Correlates multi-metric anomalies occurring within `CORRELATION_WINDOW_MINUTES` (5 mins) into **ONE** incident instead of multiple isolated alerts.
- **Deduplication Key**: Generated from host + incident family (e.g. `resource_saturation`). Prevents creating duplicate `INC-002`, `INC-003` records for continuing conditions.
- **Severity**: 4 tiers: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- **Lifecycle**: Automatically transitions to `RESOLVED` when the host returns to healthy baselines for the recovery period.

### 2.6 8-Node LangGraph Incident Analysis Workflow (`app/ai/`)
1. `collect_incident_context`: Compiles incident data, metrics, anomalies, process evidence, and logs.
2. `validate_evidence`: Formulates factual, observed evidence points (distinguished from inference).
3. `correlate_events`: Quantifies multi-metric saturation score and affected subsystems.
4. `assess_severity`: Evaluates 4-tier severity and deterministic findings.
5. `determine_root_cause`: Queries Groq LLM (`qwen/qwen3.8-27b`) with evidence constraints. Falls back to deterministic rule engine if Groq is unavailable.
6. `generate_recommendations`: Produces actionable Linux troubleshooting commands.
7. `generate_incident_summary`: Synthesizes concise reasoning summary and narrative.
8. `validate_structured_output`: Validates final payload against Pydantic schema (`LLMAnalysisOutput`).

### 2.7 Supabase PostgreSQL Storage (`app/models/`)
- Direct connection via async SQLAlchemy + asyncpg to `db.zgohttvynajravzciame.supabase.co:5432`.
- Schema: `ec2_monitoring_working`.
- Nullable metric columns ensure reality is preserved.

### 2.8 React Frontend (`frontend/src/`)
- Clean, status-focused, minimal dark/light interface.
- Format helper `formatMetric(val, suffix)` renders `null` / `undefined` as `"-"`.
- Charts with `connectNulls={false}` to avoid drawing fake zero lines.
- Manual "Collect Now" button + automatic 10-second polling.
