"""
Test specifically validating the Assessment Scenario:
At 10:00 AM:
  CPU Usage: 92%
  Memory Usage: 88%
  Disk Usage: 85%
  System Load: High
At 10:05 AM:
  CPU Usage: 96%
  Memory Usage: 91%
  Response Time: Increased
  System Load: Very High

Validates:
1. Multi-metric correlation groups all events into ONE single incident (not separate alerts).
2. Deduplication: 10:05 AM updates the existing incident without creating duplicates.
3. Severity is evaluated as CRITICAL.
4. LangGraph 8-node workflow generates structured root cause analysis with Groq / fallback.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.ai.graph import run_incident_analysis
from app.anomaly.detector import build_anomaly_model, detect_anomalies
from app.anomaly.persistence import clear_all_persistence
from app.incidents.correlation import compute_incident_key
from app.incidents.severity import determine_severity
from app.models.incident import Incident, IncidentAnomaly


@pytest.fixture(autouse=True)
def clean_state():
    clear_all_persistence()
    yield
    clear_all_persistence()


@pytest.mark.asyncio
async def test_assessment_scenario_correlation_and_deduplication():
    """
    Directly tests the Assessment Scenario described by the manager.
    """
    hostname = "ip-172-31-3-102"
    t_10_00 = datetime(2026, 9, 9, 10, 0, 0, tzinfo=timezone.utc)
    t_10_05 = datetime(2026, 9, 9, 10, 5, 0, tzinfo=timezone.utc)

    # -------------------------------------------------------------
    # Step 1: 10:00 AM Observation
    # CPU: 92%, Memory: 88%, Disk: 85%, Load: 3.5 (cpu_count = 2)
    # -------------------------------------------------------------
    anomalies_10_00 = detect_anomalies(
        hostname=hostname,
        cpu_usage=92.0,
        cpu_count=2,
        memory_usage=88.0,
        disk_usage=85.0,
        load_1m=3.5,  # > 2*cores (2.0 warning, 4.0 critical)
        response_time_ms=None,
    )

    assert len(anomalies_10_00) == 4
    metrics_10_00 = {a.metric_name for a in anomalies_10_00}
    assert metrics_10_00 == {"cpu_usage", "memory_usage", "disk_usage", "load_1m"}

    # Severity at 10:00 AM (CPU critical, Memory warning, Disk warning, Load warning)
    anomaly_models_10_00 = [
        build_anomaly_model(a, metric_id=uuid.uuid4(), timestamp=t_10_00)
        for a in anomalies_10_00
    ]
    sev_10_00 = determine_severity(anomaly_models_10_00)
    assert sev_10_00 == "CRITICAL"  # 4 simultaneous abnormal metrics

    # Correlation produces incident key
    key_10_00 = compute_incident_key(hostname, list(metrics_10_00))

    # -------------------------------------------------------------
    # Step 2: 10:05 AM Observation
    # CPU: 96%, Memory: 91%, Response Time: 2500ms, Load: 4.8
    # -------------------------------------------------------------
    anomalies_10_05 = detect_anomalies(
        hostname=hostname,
        cpu_usage=96.0,
        cpu_count=2,
        memory_usage=91.0,
        disk_usage=85.0,
        load_1m=4.8,
        response_time_ms=2500.0,
    )

    metrics_10_05 = {a.metric_name for a in anomalies_10_05}
    assert "response_time_ms" in metrics_10_05
    assert len(anomalies_10_05) == 5

    # Deduplication key maps to the same resource saturation condition
    key_10_05 = compute_incident_key(hostname, list(metrics_10_05))
    assert key_10_05 == key_10_00, "10:05 condition must match 10:00 incident key to prevent duplicate alerts"

    # Severity remains CRITICAL
    anomaly_models_10_05 = [
        build_anomaly_model(a, metric_id=uuid.uuid4(), timestamp=t_10_05)
        for a in anomalies_10_05
    ]
    sev_10_05 = determine_severity(anomaly_models_10_05)
    assert sev_10_05 == "CRITICAL"

    # -------------------------------------------------------------
    # Step 3: Run 8-Node LangGraph Workflow on the correlated event
    # -------------------------------------------------------------
    incident_data = {
        "title": "EC2 Resource Saturation",
        "hostname": hostname,
        "started_at": t_10_00.isoformat(),
        "last_seen_at": t_10_05.isoformat(),
    }
    recent_metrics = [
        {"timestamp": t_10_00.isoformat(), "cpu_usage": 92.0, "memory_usage": 88.0, "load_1m": 3.5},
        {"timestamp": t_10_05.isoformat(), "cpu_usage": 96.0, "memory_usage": 91.0, "load_1m": 4.8, "response_time_ms": 2500.0},
    ]
    anomalies_payload = [
        {"metric_name": a.metric_name, "observed_value": a.observed_value, "threshold": a.threshold, "severity": a.severity, "is_persistent": a.is_persistent}
        for a in anomalies_10_05
    ]
    process_snapshots = [
        {"name": "stress-ng", "cpu_percent": 94.5, "memory_percent": 42.0},
        {"name": "python3", "cpu_percent": 2.0, "memory_percent": 5.0},
    ]

    analysis_state = await run_incident_analysis(
        incident_id=str(uuid.uuid4()),
        hostname=hostname,
        incident_data=incident_data,
        recent_metrics=recent_metrics,
        anomalies=anomalies_payload,
        process_snapshots=process_snapshots,
        correlation_score=8.5,
    )

    # Validate output structure
    assert analysis_state["assessed_severity"] == "CRITICAL"
    assert "cpu_usage" in analysis_state["affected_metrics"]
    assert "memory_usage" in analysis_state["affected_metrics"]
    assert "load_1m" in analysis_state["affected_metrics"]
    assert analysis_state["probable_cause"] is not None
    assert len(analysis_state["probable_cause"]) > 20
    assert len(analysis_state["recommended_actions"]) >= 2
    assert analysis_state["confidence"] >= 0.70
    assert analysis_state["validation_passed"] is True

    # Validate Event Relationship analysis (Causal link between resource exhaustion and response time degradation)
    assert analysis_state.get("event_relationship") is not None
    rel_text = analysis_state["event_relationship"].lower()
    assert any(k in rel_text for k in ("related", "unified", "cascade", "caus", "saturation", "underlying"))

    from app.incidents.correlation import analyze_event_relationship
    rel = analyze_event_relationship(anomaly_models_10_05)
    assert "related" in rel.lower()
    assert "response time" in rel.lower()
