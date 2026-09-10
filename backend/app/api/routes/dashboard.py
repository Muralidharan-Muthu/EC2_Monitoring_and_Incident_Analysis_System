"""
Dashboard and system status API routes.

GET /api/dashboard/summary    — summary data for the overview panel
GET /api/dashboard/timeseries — time-series for multiple metrics
GET /api/system/status        — overall system health status
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.incident_repository import IncidentRepository
from app.repositories.metric_repository import MetricRepository
from app.schemas.analysis import DashboardSummary, TimeSeriesPoint, TimeSeriesResponse

router = APIRouter()
settings = get_settings()


def _determine_system_status(
    active_count: int, highest_severity: Optional[str], latest_cpu: Optional[float]
) -> str:
    """Derive a top-level system status string."""
    if active_count == 0:
        return "HEALTHY"
    if highest_severity == "CRITICAL":
        return "CRITICAL"
    return "DEGRADED"


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummary,
    tags=["Dashboard"],
    summary="Dashboard overview summary",
)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    """
    Return current system status, active incident count, and latest metric values.

    Designed to power the dashboard top-level status panel.
    """
    metric_repo = MetricRepository(db)
    incident_repo = IncidentRepository(db)

    latest = await metric_repo.get_latest()
    latest_valid = await metric_repo.get_latest_valid()
    active_metric = latest_valid if (latest and latest.cpu_usage is None) else latest

    active_count = await incident_repo.count_active()
    active_incidents = await incident_repo.get_active_incidents()
    severities = [i.severity for i in active_incidents]
    highest_severity = (
        "CRITICAL" if "CRITICAL" in severities else "WARNING" if severities else None
    )

    # Determine SSH freshness and connection status
    if latest is None and latest_valid is None:
        ssh_status = "UNAVAILABLE"
        system_status = "UNAVAILABLE"
    elif latest and (latest.cpu_usage is None and latest.memory_usage is None):
        ssh_status = "UNAVAILABLE"
        system_status = "UNAVAILABLE"
    else:
        metric_for_time = latest or latest_valid
        now_utc = datetime.now(tz=timezone.utc)
        ts = metric_for_time.timestamp if metric_for_time.timestamp.tzinfo else metric_for_time.timestamp.replace(tzinfo=timezone.utc)
        age = (now_utc - ts).total_seconds()
        if age > 120:
            ssh_status = "DEGRADED"
            system_status = "DEGRADED"
        else:
            ssh_status = "CONNECTED"
            system_status = _determine_system_status(
                active_count, highest_severity, active_metric.cpu_usage if active_metric else None
            )

    return DashboardSummary(
        system_status=system_status,
        active_incident_count=active_count,
        highest_severity=highest_severity,
        latest_cpu=active_metric.cpu_usage if active_metric else None,
        latest_memory=active_metric.memory_usage if active_metric else None,
        latest_disk=active_metric.disk_usage if active_metric else None,
        latest_load_1m=active_metric.load_1m if active_metric else None,
        latest_response_time_ms=active_metric.response_time_ms if active_metric else None,
        hostname=active_metric.hostname if active_metric else (latest.hostname if latest else (settings.ec2_host or None)),
        last_metric_at=active_metric.timestamp.isoformat() if active_metric else (latest.timestamp.isoformat() if latest else None),
        ssh_status=ssh_status,
        ec2_host_configured=bool(settings.ec2_host),
        aws_region=settings.aws_region or "ap-south-1",
    )


@router.get(
    "/dashboard/timeseries",
    response_model=TimeSeriesResponse,
    tags=["Dashboard"],
    summary="Multi-metric time-series for dashboard charts",
)
async def get_dashboard_timeseries(
    hostname: Optional[str] = Query(None),
    minutes: int = Query(default=60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
) -> TimeSeriesResponse:
    """Return time-series data for the dashboard chart panel."""
    repo = MetricRepository(db)
    metrics = await repo.get_history(hostname=hostname, minutes=minutes, limit=500)

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

    return TimeSeriesResponse(
        data=points,
        hostname=metrics[0].hostname if metrics else hostname,
        range_minutes=minutes,
    )


@router.get(
    "/system/status",
    tags=["System"],
    summary="Detailed system health status",
)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return detailed health status including metric freshness."""
    metric_repo = MetricRepository(db)
    incident_repo = IncidentRepository(db)

    latest = await metric_repo.get_latest()
    active_count = await incident_repo.count_active()
    total_metrics = await metric_repo.count()

    age_seconds = None
    if latest:
        now = datetime.now(tz=timezone.utc)
        last_ts = latest.timestamp.replace(tzinfo=timezone.utc) if latest.timestamp.tzinfo is None else latest.timestamp
        age_seconds = (now - last_ts).total_seconds()

    return {
        "service": "EC2 Monitoring System",
        "version": "1.0.0",
        "database": "connected",
        "total_metrics": total_metrics,
        "active_incidents": active_count,
        "latest_metric_age_seconds": age_seconds,
        "monitoring_agent_active": age_seconds is not None and age_seconds < 120,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
