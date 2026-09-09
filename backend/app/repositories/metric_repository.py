"""
Metric repository — database access layer for metrics and process snapshots.

All raw SQL/ORM queries related to metrics live here.
Services call these methods and do not construct queries themselves.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.metric import Metric, ProcessSnapshot


class MetricRepository:
    """Data-access object for Metric and ProcessSnapshot records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, metric: Metric) -> Metric:
        """Persist a new metric record."""
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    async def create_process_snapshot(self, snapshot: ProcessSnapshot) -> ProcessSnapshot:
        """Persist a process snapshot record."""
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def get_latest(self, hostname: Optional[str] = None) -> Optional[Metric]:
        """Return the most recent metric record, optionally filtered by hostname."""
        q = select(Metric).order_by(desc(Metric.timestamp)).limit(1)
        if hostname:
            q = q.where(Metric.hostname == hostname)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_history(
        self,
        hostname: Optional[str] = None,
        minutes: int = 60,
        limit: int = 1000,
    ) -> list[Metric]:
        """
        Return metric history for the specified time range.

        Args:
            hostname: Filter by hostname. If None, returns all hosts.
            minutes: How far back in time to look.
            limit: Maximum number of records to return.
        """
        since = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
        q = (
            select(Metric)
            .where(Metric.timestamp >= since)
            .order_by(Metric.timestamp)
            .limit(limit)
        )
        if hostname:
            q = q.where(Metric.hostname == hostname)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_recent_for_hostname(
        self, hostname: str, limit: int = 10
    ) -> list[Metric]:
        """Return the N most recent metrics for a specific host."""
        q = (
            select(Metric)
            .where(Metric.hostname == hostname)
            .order_by(desc(Metric.timestamp))
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return total number of metric records."""
        result = await self.db.execute(select(func.count()).select_from(Metric))
        return result.scalar_one()

    async def get_by_id(self, metric_id: uuid.UUID) -> Optional[Metric]:
        """Return a specific metric by ID."""
        result = await self.db.execute(
            select(Metric).where(Metric.id == metric_id)
        )
        return result.scalar_one_or_none()

    async def get_process_snapshots_for_metric(
        self, metric_id: uuid.UUID
    ) -> list[ProcessSnapshot]:
        """Return process snapshots associated with a metric."""
        result = await self.db.execute(
            select(ProcessSnapshot).where(ProcessSnapshot.metric_id == metric_id)
        )
        return list(result.scalars().all())
