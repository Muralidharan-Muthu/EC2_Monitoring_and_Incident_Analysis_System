"""
Anomaly repository — database access for anomaly records.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import Anomaly


class AnomalyRepository:
    """Data-access object for Anomaly records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, anomaly: Anomaly) -> Anomaly:
        """Persist a new anomaly."""
        self.db.add(anomaly)
        await self.db.flush()
        await self.db.refresh(anomaly)
        return anomaly

    async def get_recent(
        self,
        minutes: int = 30,
        hostname: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 200,
    ) -> list[Anomaly]:
        """Return recent anomalies within the specified time window."""
        since = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
        q = (
            select(Anomaly)
            .where(Anomaly.detected_at >= since)
            .order_by(desc(Anomaly.detected_at))
            .limit(limit)
        )
        if severity:
            q = q.where(Anomaly.severity == severity)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, anomaly_id: uuid.UUID) -> Optional[Anomaly]:
        result = await self.db.execute(
            select(Anomaly).where(Anomaly.id == anomaly_id)
        )
        return result.scalar_one_or_none()

    async def get_for_metric(self, metric_id: uuid.UUID) -> list[Anomaly]:
        """Return all anomalies for a specific metric."""
        result = await self.db.execute(
            select(Anomaly).where(Anomaly.metric_id == metric_id)
        )
        return list(result.scalars().all())

    async def count_recent(self, minutes: int = 60) -> int:
        since = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
        result = await self.db.execute(
            select(func.count())
            .select_from(Anomaly)
            .where(Anomaly.detected_at >= since)
        )
        return result.scalar_one()
