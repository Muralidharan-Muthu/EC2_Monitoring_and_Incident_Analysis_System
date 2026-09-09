"""
Metrics API routes.

POST /api/metrics       — receive metrics from the monitoring agent
GET  /api/metrics/latest — latest metric snapshot
GET  /api/metrics/history — historical metrics for charting
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_agent_api_key
from app.repositories.metric_repository import MetricRepository
from app.schemas.metric import MetricIngest, MetricIngestResponse, MetricResponse
from app.schemas.analysis import TimeSeriesPoint, TimeSeriesResponse
from app.services.metric_service import MetricService

router = APIRouter()


@router.post(
    "/metrics",
    response_model=MetricIngestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_agent_api_key)],
    tags=["Metrics"],
    summary="Ingest a metric observation from the monitoring agent",
)
async def ingest_metric(
    payload: MetricIngest,
    db: AsyncSession = Depends(get_db),
) -> MetricIngestResponse:
    """
    Receive a system metrics payload from the monitoring agent.

    Triggers:
    1. Metric persistence
    2. Process snapshot persistence
    3. Rule-based anomaly detection
    4. Incident correlation and lifecycle management
    """
    svc = MetricService(db)
    metric, anomalies, incident = await svc.ingest(payload)

    return MetricIngestResponse(
        metric_id=metric.id,
        anomalies_detected=len(anomalies),
        incident_id=incident.id if incident else None,
        message=(
            f"Metric ingested. {len(anomalies)} anomaly/anomalies detected."
            if anomalies
            else "Metric ingested. System operating normally."
        ),
    )


@router.get(
    "/metrics/latest",
    response_model=Optional[MetricResponse],
    tags=["Metrics"],
    summary="Get the most recent metric snapshot",
)
async def get_latest_metric(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    db: AsyncSession = Depends(get_db),
) -> Optional[MetricResponse]:
    """Return the most recent metric record."""
    repo = MetricRepository(db)
    metric = await repo.get_latest(hostname=hostname)
    if metric is None:
        return None
    return MetricResponse.model_validate(metric)


@router.get(
    "/metrics/history",
    response_model=TimeSeriesResponse,
    tags=["Metrics"],
    summary="Get historical metrics for time-series charts",
)
async def get_metric_history(
    hostname: Optional[str] = Query(None),
    minutes: int = Query(default=60, ge=1, le=1440, description="Look-back period in minutes"),
    db: AsyncSession = Depends(get_db),
) -> TimeSeriesResponse:
    """
    Return time-series metric data for the given period.

    Used by the frontend to render CPU, memory, disk, and load charts.
    """
    repo = MetricRepository(db)
    metrics = await repo.get_history(hostname=hostname, minutes=minutes)

    points = [
        TimeSeriesPoint(
            timestamp=m.timestamp.isoformat(),
            cpu_usage=m.cpu_usage,
            memory_usage=m.memory_usage,
            disk_usage=m.disk_usage,
            load_1m=m.load_1m,
            response_time_ms=m.response_time_ms,
        )
        for m in metrics
    ]

    detected_hostname = metrics[0].hostname if metrics else hostname

    return TimeSeriesResponse(
        data=points,
        hostname=detected_hostname,
        range_minutes=minutes,
    )
