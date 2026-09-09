"""
Anomalies API routes.

GET /api/anomalies — list recent anomalies
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.anomaly_repository import AnomalyRepository
from app.schemas.anomaly import AnomalyListResponse, AnomalyResponse

router = APIRouter()


@router.get(
    "/anomalies",
    response_model=AnomalyListResponse,
    tags=["Anomalies"],
    summary="List recently detected anomalies",
)
async def list_anomalies(
    minutes: int = Query(default=60, ge=1, le=1440),
    severity: Optional[str] = Query(None, pattern="^(WARNING|CRITICAL)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AnomalyListResponse:
    """
    Return anomalies detected within the specified time window.

    Supports filtering by severity and pagination.
    """
    repo = AnomalyRepository(db)
    offset = (page - 1) * page_size
    anomalies = await repo.get_recent(
        minutes=minutes, severity=severity, limit=page_size + offset
    )
    # Simple in-memory pagination (DB-level pagination can be added for scale)
    paginated = anomalies[offset : offset + page_size]
    total = await repo.count_recent(minutes=minutes)

    return AnomalyListResponse(
        anomalies=[AnomalyResponse.model_validate(a) for a in paginated],
        total=total,
        page=page,
        page_size=page_size,
    )
