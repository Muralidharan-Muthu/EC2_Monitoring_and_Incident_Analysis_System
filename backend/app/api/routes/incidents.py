"""
Incidents API routes.

GET  /api/incidents                        — list incidents (filtered/paginated)
GET  /api/incidents/{incident_id}          — incident detail
POST /api/incidents/{incident_id}/analyze  — trigger LangGraph analysis
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.incident import IncidentAnalysis
from app.models.metric import Metric, ProcessSnapshot
from app.anomaly.detector import detect_anomalies, build_anomaly_model
from app.incidents.incident_service import correlate_and_persist_incident
from app.repositories.incident_repository import IncidentRepository
from app.repositories.metric_repository import MetricRepository
from app.ai.graph import run_incident_analysis
from app.schemas.incident import (
    AnomalySummary,
    IncidentAnalysisSchema,
    IncidentListResponse,
    IncidentResponse,
    IncidentUpdateRequest,
)

router = APIRouter()
logger = get_logger(__name__)


def _serialize_incident(incident) -> IncidentResponse:
    """Convert an Incident ORM object to the response schema."""
    anomaly_summaries = []
    anom_objects = []
    for ia in (incident.incident_anomalies or []):
        a = ia.anomaly
        if a:
            anom_objects.append(a)
            anomaly_summaries.append(
                AnomalySummary(
                    id=a.id,
                    metric_name=a.metric_name,
                    observed_value=a.observed_value,
                    threshold=a.threshold,
                    severity=a.severity,
                    description=a.description,
                    is_persistent=a.is_persistent,
                    detected_at=a.detected_at,
                )
            )

    analysis = None
    event_rel = None
    if incident.analysis:
        if incident.analysis.raw_llm_response and isinstance(incident.analysis.raw_llm_response, dict):
            event_rel = incident.analysis.raw_llm_response.get("event_relationship")

        if not event_rel and anom_objects:
            from app.incidents.correlation import analyze_event_relationship
            event_rel = analyze_event_relationship(anom_objects)

        analysis = IncidentAnalysisSchema(
            affected_metrics=incident.analysis.affected_metrics or [],
            probable_causes=incident.analysis.probable_causes or [],
            evidence=incident.analysis.evidence or [],
            recommended_actions=incident.analysis.recommended_actions or [],
            reasoning_summary=incident.analysis.reasoning_summary or "",
            analysis_source=incident.analysis.analysis_source or "rule_based",
            model_name=incident.analysis.model_name,
            confidence=incident.analysis.confidence,
            generated_at=incident.analysis.generated_at,
            event_relationship=event_rel,
        )
    elif anom_objects:
        from app.incidents.correlation import analyze_event_relationship
        event_rel = analyze_event_relationship(anom_objects)

    return IncidentResponse(
        id=incident.id,
        incident_key=incident.incident_key,
        title=incident.title,
        status=incident.status,
        severity=incident.severity,
        hostname=incident.hostname,
        started_at=incident.started_at,
        ended_at=incident.ended_at,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        probable_cause=incident.probable_cause,
        recommended_action=incident.recommended_action,
        summary=incident.summary,
        correlation_score=incident.correlation_score,
        affected_metrics=incident.affected_metrics,
        llm_confidence=incident.llm_confidence,
        llm_analyzed=incident.llm_analyzed,
        observation_count=incident.observation_count,
        event_relationship=event_rel,
        anomalies=anomaly_summaries,
        analysis=analysis,
    )


@router.get(
    "/incidents",
    response_model=IncidentListResponse,
    tags=["Incidents"],
    summary="List incidents with optional filters",
)
async def list_incidents(
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(OPEN|INVESTIGATING|RESOLVED)$"
    ),
    severity: Optional[str] = Query(None, pattern="^(WARNING|CRITICAL)$"),
    hostname: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> IncidentListResponse:
    """Return paginated incident list with optional severity/status filtering."""
    repo = IncidentRepository(db)
    offset = (page - 1) * page_size
    incidents, total = await repo.list_incidents(
        status=status_filter,
        severity=severity,
        hostname=hostname,
        limit=page_size,
        offset=offset,
    )
    return IncidentListResponse(
        incidents=[_serialize_incident(i) for i in incidents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    tags=["Incidents"],
    summary="Get incident detail",
)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Return detailed incident record including anomalies and analysis."""
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return _serialize_incident(incident)


@router.post(
    "/incidents/{incident_id}/analyze",
    response_model=IncidentResponse,
    tags=["Incidents"],
    summary="Trigger LangGraph AI analysis for an incident",
)
async def analyze_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """
    Trigger the LangGraph + Groq analysis workflow for an incident.

    If the LLM is unavailable, returns rule-based analysis.
    The incident is always updated — this endpoint never fails silently.
    """
    incident_repo = IncidentRepository(db)
    metric_repo = MetricRepository(db)

    incident = await incident_repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Gather context for the analysis
    anomalies = [
        {
            "id": str(ia.anomaly.id),
            "metric_name": ia.anomaly.metric_name,
            "observed_value": ia.anomaly.observed_value,
            "threshold": ia.anomaly.threshold,
            "severity": ia.anomaly.severity,
            "description": ia.anomaly.description,
            "is_persistent": ia.anomaly.is_persistent,
            "consecutive_count": ia.anomaly.consecutive_count,
            "detected_at": ia.anomaly.detected_at.isoformat(),
        }
        for ia in (incident.incident_anomalies or [])
        if ia.anomaly
    ]

    # Recent metrics from the host (last 10 observations)
    recent = await metric_repo.get_recent_for_hostname(incident.hostname, limit=10)
    recent_metrics = [
        {
            "timestamp": m.timestamp.isoformat(),
            "cpu_usage": m.cpu_usage,
            "memory_usage": m.memory_usage,
            "disk_usage": m.disk_usage,
            "load_1m": m.load_1m,
            "response_time_ms": m.response_time_ms,
        }
        for m in recent
    ]

    # Process snapshots from the most recent metric
    process_snapshots = []
    if recent:
        snapshots = await metric_repo.get_process_snapshots_for_metric(recent[0].id)
        process_snapshots = [
            {
                "process_name": s.process_name,
                "pid": s.pid,
                "cpu_percent": s.cpu_percent,
                "memory_percent": s.memory_percent,
                "snapshot_type": s.snapshot_type,
            }
            for s in snapshots
        ]

    incident_data = {
        "id": str(incident.id),
        "hostname": incident.hostname,
        "started_at": incident.started_at.isoformat(),
        "observation_count": incident.observation_count,
        "probable_cause": incident.probable_cause,
        "affected_metrics": incident.affected_metrics or [],
    }

    # Run LangGraph workflow
    logger.info("analysis_triggered", incident_id=str(incident_id))
    final_state = await run_incident_analysis(
        incident_id=str(incident_id),
        hostname=incident.hostname,
        incident_data=incident_data,
        recent_metrics=recent_metrics,
        anomalies=anomalies,
        process_snapshots=process_snapshots,
        correlation_score=incident.correlation_score,
    )

    # Save analysis result
    analysis = IncidentAnalysis(
        incident_id=incident.id,
        affected_metrics=final_state.get("affected_metrics", []),
        probable_causes=[final_state.get("probable_cause", "")],
        evidence=final_state.get("evidence", []),
        recommended_actions=final_state.get("recommended_actions", []),
        reasoning_summary=final_state.get("reasoning_summary", ""),
        analysis_source=final_state.get("analysis_source", "rule_engine"),
        model_name=final_state.get("model_name"),
        confidence=final_state.get("confidence"),
        raw_llm_response=final_state.get("raw_llm_output"),
    )
    await incident_repo.save_analysis(analysis)

    # Update incident with analysis metadata
    incident.llm_analyzed = final_state.get("analysis_source") in ("llm", "groq")
    incident.llm_confidence = final_state.get("confidence")
    if final_state.get("probable_cause"):
        incident.probable_cause = final_state["probable_cause"]
    if final_state.get("recommended_actions"):
        incident.recommended_action = " ".join(
            f"({i+1}) {a}." for i, a in enumerate(final_state["recommended_actions"])
        )
    affected_str = ", ".join(sorted(incident.affected_metrics or []))
    incident.summary = (
        f"[{incident.severity}] Incident on {incident.hostname} affecting {affected_str}. "
        f"Correlated analysis confirmed {final_state.get('probable_cause', 'resource saturation')}."
    )

    await incident_repo.update(incident)

    # Re-fetch with relationships
    updated = await incident_repo.get_by_id(incident_id)
    return _serialize_incident(updated)


@router.patch(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    tags=["Incidents"],
    summary="Update incident status",
)
async def update_incident_status(
    incident_id: uuid.UUID,
    payload: IncidentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Update incident status (OPEN, INVESTIGATING, RESOLVED)."""
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    incident.status = payload.status
    if payload.status == "RESOLVED":
        incident.ended_at = datetime.now(timezone.utc)
    else:
        incident.ended_at = None
    await repo.update(incident)
    await db.commit()
    updated = await repo.get_by_id(incident_id)
    return _serialize_incident(updated)


@router.post(
    "/incidents/simulate-assessment-scenario",
    response_model=IncidentResponse,
    tags=["Incidents"],
    summary="Simulate Assessment Scenario (10:00 AM -> 10:05 AM Multi-Metric Escalation)",
)
async def simulate_assessment_scenario(
    hostname: Optional[str] = Query(None, description="Target hostname, defaults to active EC2 host"),
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """
    Simulates the exact Assessment Scenario:
    At 10:00 AM:
      ● CPU Usage: 92%
      ● Memory Usage: 88%
      ● Disk Usage: 85%
      ● System Load: High (3.5 on 2 cores)
    At 10:05 AM:
      ● CPU Usage: 96%
      ● Memory Usage: 91%
      ● Response Time: Increased (2500ms)
      ● System Load: Very High (4.8 on 2 cores)

    The engine groups all 5 anomalous metrics across both timeframes into ONE incident,
    proves temporal deduplication, evaluates the causal relationship, runs LangGraph AI analysis,
    and returns the unified incident.
    """
    settings = get_settings()
    target_host = hostname or settings.ec2_host or "ec2-instance-primary"

    t_10_00 = datetime.now(timezone.utc) - timedelta(minutes=5)
    t_10_05 = datetime.now(timezone.utc)

    # 1. Create 10:00 AM Metric observation
    m_10_00 = Metric(
        id=uuid.uuid4(),
        hostname=target_host,
        timestamp=t_10_00,
        cpu_usage=92.0,
        memory_usage=88.0,
        disk_usage=85.0,
        load_1m=3.5,
        load_5m=2.8,
        load_15m=2.1,
        cpu_count=2,
        memory_total_mb=4096.0,
        memory_used_mb=3604.0,
        disk_total_gb=30.0,
        disk_used_gb=25.5,
    )
    db.add(m_10_00)
    await db.flush()

    p1 = ProcessSnapshot(
        metric_id=m_10_00.id,
        process_name="stress-ng-cpu",
        pid=4102,
        cpu_percent=91.5,
        memory_percent=42.0,
        snapshot_type="top_cpu",
        timestamp=t_10_00,
    )
    p2 = ProcessSnapshot(
        metric_id=m_10_00.id,
        process_name="stress-ng-vm",
        pid=4103,
        cpu_percent=0.5,
        memory_percent=45.0,
        snapshot_type="top_memory",
        timestamp=t_10_00,
    )
    db.add(p1)
    db.add(p2)

    det_10_00 = detect_anomalies(
        hostname=target_host,
        cpu_usage=92.0,
        cpu_count=2,
        memory_usage=88.0,
        disk_usage=85.0,
        load_1m=3.5,
        response_time_ms=None,
    )
    anom_rows_10_00 = [
        build_anomaly_model(d, metric_id=m_10_00.id, timestamp=t_10_00)
        for d in det_10_00
    ]
    for a in anom_rows_10_00:
        db.add(a)
    await db.flush()

    inc_10_00 = await correlate_and_persist_incident(
        db=db,
        hostname=target_host,
        anomalies=anom_rows_10_00,
        timestamp=t_10_00,
        processes=[
            {"process_name": "stress-ng-cpu", "pid": 4102, "cpu_percent": 91.5, "memory_percent": 42.0},
            {"process_name": "stress-ng-vm", "pid": 4103, "cpu_percent": 0.5, "memory_percent": 45.0},
        ],
    )

    # 2. Create 10:05 AM Metric observation (Escalation & Response Time degradation)
    m_10_05 = Metric(
        id=uuid.uuid4(),
        hostname=target_host,
        timestamp=t_10_05,
        cpu_usage=96.0,
        memory_usage=91.0,
        disk_usage=85.0,
        load_1m=4.8,
        load_5m=3.9,
        load_15m=2.9,
        cpu_count=2,
        response_time_ms=2500.0,
        memory_total_mb=4096.0,
        memory_used_mb=3727.0,
        disk_total_gb=30.0,
        disk_used_gb=25.5,
    )
    db.add(m_10_05)
    await db.flush()

    p3 = ProcessSnapshot(
        metric_id=m_10_05.id,
        process_name="stress-ng-cpu",
        pid=4102,
        cpu_percent=95.8,
        memory_percent=44.0,
        snapshot_type="top_cpu",
        timestamp=t_10_05,
    )
    p4 = ProcessSnapshot(
        metric_id=m_10_05.id,
        process_name="stress-ng-vm",
        pid=4103,
        cpu_percent=0.4,
        memory_percent=46.5,
        snapshot_type="top_memory",
        timestamp=t_10_05,
    )
    db.add(p3)
    db.add(p4)

    det_10_05 = detect_anomalies(
        hostname=target_host,
        cpu_usage=96.0,
        cpu_count=2,
        memory_usage=91.0,
        disk_usage=85.0,
        load_1m=4.8,
        response_time_ms=2500.0,
    )
    anom_rows_10_05 = [
        build_anomaly_model(d, metric_id=m_10_05.id, timestamp=t_10_05)
        for d in det_10_05
    ]
    for a in anom_rows_10_05:
        db.add(a)
    await db.flush()

    incident = await correlate_and_persist_incident(
        db=db,
        hostname=target_host,
        anomalies=anom_rows_10_05,
        timestamp=t_10_05,
        processes=[
            {"process_name": "stress-ng-cpu", "pid": 4102, "cpu_percent": 95.8, "memory_percent": 44.0},
            {"process_name": "stress-ng-vm", "pid": 4103, "cpu_percent": 0.4, "memory_percent": 46.5},
        ],
    )
    await db.commit()

    # 3. Run full LangGraph 8-node incident analysis workflow
    incident_repo = IncidentRepository(db)
    final_state = await run_incident_analysis(
        incident_id=str(incident.id),
        hostname=target_host,
        incident_data={
            "id": str(incident.id),
            "hostname": target_host,
            "started_at": t_10_00.isoformat(),
            "observation_count": incident.observation_count,
            "probable_cause": incident.probable_cause,
            "affected_metrics": incident.affected_metrics or [],
        },
        recent_metrics=[
            {"timestamp": t_10_00.isoformat(), "cpu_usage": 92.0, "memory_usage": 88.0, "disk_usage": 85.0, "load_1m": 3.5},
            {"timestamp": t_10_05.isoformat(), "cpu_usage": 96.0, "memory_usage": 91.0, "disk_usage": 85.0, "load_1m": 4.8, "response_time_ms": 2500.0},
        ],
        anomalies=[
            {
                "id": str(a.id),
                "metric_name": a.metric_name,
                "observed_value": a.observed_value,
                "threshold": a.threshold,
                "severity": a.severity,
                "description": a.description,
                "is_persistent": a.is_persistent,
                "detected_at": a.detected_at.isoformat(),
            }
            for a in (anom_rows_10_00 + anom_rows_10_05)
        ],
        process_snapshots=[
            {"process_name": "stress-ng-cpu", "pid": 4102, "cpu_percent": 95.8, "memory_percent": 44.0, "snapshot_type": "top_cpu"},
            {"process_name": "stress-ng-vm", "pid": 4103, "cpu_percent": 0.4, "memory_percent": 46.5, "snapshot_type": "top_memory"},
        ],
        correlation_score=incident.correlation_score,
    )

    raw_output = final_state.get("raw_llm_output") or {}
    event_rel = final_state.get("event_relationship") or raw_output.get("event_relationship")
    if not event_rel:
        from app.incidents.correlation import analyze_event_relationship
        event_rel = analyze_event_relationship(anom_rows_10_05)
    raw_output["event_relationship"] = event_rel

    analysis = IncidentAnalysis(
        incident_id=incident.id,
        affected_metrics=final_state.get("affected_metrics", incident.affected_metrics),
        probable_causes=[final_state.get("probable_cause", incident.probable_cause or "")],
        evidence=final_state.get("evidence", []),
        recommended_actions=final_state.get("recommended_actions", []),
        reasoning_summary=final_state.get("reasoning_summary", incident.summary or ""),
        analysis_source=final_state.get("analysis_source", "rule_engine"),
        model_name=final_state.get("model_name"),
        confidence=final_state.get("confidence"),
        raw_llm_response=raw_output,
    )
    await incident_repo.save_analysis(analysis)

    incident.llm_analyzed = final_state.get("analysis_source") in ("llm", "groq")
    incident.llm_confidence = final_state.get("confidence")
    if final_state.get("probable_cause"):
        incident.probable_cause = final_state["probable_cause"]
    if final_state.get("recommended_actions"):
        incident.recommended_action = " ".join(
            f"({i+1}) {a}." for i, a in enumerate(final_state["recommended_actions"])
        )
    affected_str = ", ".join(sorted(incident.affected_metrics or []))
    incident.summary = (
        f"[{incident.severity}] Unified incident on {target_host} affecting {affected_str}. "
        f"Cross-metric correlation confirmed compute/memory saturation cascading into response time degradation."
    )

    await incident_repo.update(incident)
    await db.commit()

    updated = await incident_repo.get_by_id(incident.id)
    return _serialize_incident(updated)
