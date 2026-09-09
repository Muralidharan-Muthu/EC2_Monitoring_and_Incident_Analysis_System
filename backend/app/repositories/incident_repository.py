"""
Incident repository — database access for incident records.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentAnomaly, IncidentAnalysis
from app.models.anomaly import Anomaly


class IncidentRepository:
    """Data-access object for Incident records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, incident: Incident) -> Incident:
        """Persist a new incident."""
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def update(self, incident: Incident) -> Incident:
        """Flush an updated incident."""
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def get_by_id(self, incident_id: uuid.UUID) -> Optional[Incident]:
        """Return an incident with its anomalies and analysis eagerly loaded."""
        result = await self.db.execute(
            select(Incident)
            .options(
                selectinload(Incident.incident_anomalies).selectinload(
                    IncidentAnomaly.anomaly
                ),
                selectinload(Incident.analysis),
            )
            .where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, incident_key: str) -> Optional[Incident]:
        """Return an incident by its deduplication key."""
        result = await self.db.execute(
            select(Incident).where(Incident.incident_key == incident_key)
        )
        return result.scalar_one_or_none()

    async def get_active_by_key(self, incident_key: str) -> Optional[Incident]:
        """Return an open/investigating incident by its deduplication key."""
        result = await self.db.execute(
            select(Incident).where(
                and_(
                    Incident.incident_key == incident_key,
                    Incident.status.in_(["OPEN", "INVESTIGATING"]),
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        hostname: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Incident], int]:
        """Return paginated incidents with total count."""
        base_q = select(Incident)
        count_q = select(func.count()).select_from(Incident)

        filters = []
        if status:
            filters.append(Incident.status == status)
        if severity:
            filters.append(Incident.severity == severity)
        if hostname:
            filters.append(Incident.hostname == hostname)

        if filters:
            base_q = base_q.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        items_result = await self.db.execute(
            base_q.options(
                selectinload(Incident.incident_anomalies).selectinload(
                    IncidentAnomaly.anomaly
                ),
                selectinload(Incident.analysis),
            )
            .order_by(desc(Incident.started_at))
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def get_active_incidents(self) -> list[Incident]:
        """Return all open or investigating incidents."""
        result = await self.db.execute(
            select(Incident).where(
                Incident.status.in_(["OPEN", "INVESTIGATING"])
            )
        )
        return list(result.scalars().all())

    async def link_anomaly(self, incident: Incident, anomaly: Anomaly) -> None:
        """Create an IncidentAnomaly join record if not already present."""
        existing = await self.db.execute(
            select(IncidentAnomaly).where(
                and_(
                    IncidentAnomaly.incident_id == incident.id,
                    IncidentAnomaly.anomaly_id == anomaly.id,
                )
            )
        )
        if existing.scalar_one_or_none() is None:
            link = IncidentAnomaly(incident_id=incident.id, anomaly_id=anomaly.id)
            self.db.add(link)
            await self.db.flush()

    async def save_analysis(self, analysis: IncidentAnalysis) -> IncidentAnalysis:
        """Persist (upsert) an incident analysis record."""
        # Delete existing if present
        existing = await self.db.execute(
            select(IncidentAnalysis).where(
                IncidentAnalysis.incident_id == analysis.incident_id
            )
        )
        existing_record = existing.scalar_one_or_none()
        if existing_record:
            await self.db.delete(existing_record)
            await self.db.flush()
        self.db.add(analysis)
        await self.db.flush()
        await self.db.refresh(analysis)
        return analysis

    async def count_active(self) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Incident)
            .where(Incident.status.in_(["OPEN", "INVESTIGATING"]))
        )
        return result.scalar_one()
