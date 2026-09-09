"""
Incidents API routes.

GET  /api/incidents                        — list incidents (filtered/paginated)
GET  /api/incidents/{incident_id}          — incident detail
POST /api/incidents/{incident_id}/analyze  — trigger LangGraph analysis
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.incident import IncidentAnalysis
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
    for ia in (incident.incident_anomalies or []):
        a = ia.anomaly
        if a:
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
    if incident.analysis:
        analysis = IncidentAnalysisSchema.model_validate(incident.analysis)

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
    if final_state.get("reasoning_summary"):
        incident.summary = final_state["reasoning_summary"]

    await incident_repo.update(incident)

    # Re-fetch with relationships
    updated = await incident_repo.get_by_id(incident_id)
    return _serialize_incident(updated)
