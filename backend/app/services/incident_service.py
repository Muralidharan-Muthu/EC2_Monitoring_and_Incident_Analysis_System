"""
Incident service — manages the full incident lifecycle.

Responsibilities:
  - Create new incidents from correlated anomalies.
  - Update existing incidents with new observations (deduplication).
  - Resolve incidents when conditions return to normal.
  - Ensure one incident per correlated condition rather than alert storm.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.anomaly import Anomaly
from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.services.correlation_engine import (
    build_incident_title,
    compute_correlation_score,
    compute_incident_key,
    determine_severity,
    generate_rule_based_cause,
    generate_rule_based_recommendation,
)

logger = get_logger(__name__)


class IncidentService:
    """Manages incident creation, deduplication, and lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncidentRepository(db)
        self.settings = get_settings()

    async def process_anomalies(
        self,
        hostname: str,
        anomalies: list[Anomaly],
        metric_timestamp: datetime,
    ) -> Optional[Incident]:
        """
        Given a set of detected anomalies, either:
          - Create a new incident, or
          - Update an existing active incident.

        Returns the incident (new or updated), or None if no incident warranted.
        """
        if not anomalies:
            return None

        affected_metrics = list({a.metric_name for a in anomalies})
        incident_key = compute_incident_key(hostname, affected_metrics)
        correlation_score = compute_correlation_score(anomalies)
        severity = determine_severity(anomalies)

        # Check for an existing active incident with the same key
        existing = await self.repo.get_active_by_key(incident_key)

        if existing:
            return await self._update_incident(
                incident=existing,
                anomalies=anomalies,
                correlation_score=correlation_score,
                severity=severity,
                affected_metrics=affected_metrics,
            )
        else:
            return await self._create_incident(
                hostname=hostname,
                anomalies=anomalies,
                affected_metrics=affected_metrics,
                incident_key=incident_key,
                correlation_score=correlation_score,
                severity=severity,
                started_at=metric_timestamp,
            )

    async def _create_incident(
        self,
        hostname: str,
        anomalies: list[Anomaly],
        affected_metrics: list[str],
        incident_key: str,
        correlation_score: float,
        severity: str,
        started_at: datetime,
    ) -> Incident:
        """Create a new incident and link anomalies to it."""
        title = build_incident_title(affected_metrics, severity)
        probable_cause = generate_rule_based_cause(anomalies)
        recommended_action = generate_rule_based_recommendation(anomalies)

        summary = (
            f"Detected {len(anomalies)} correlated anomaly/anomalies on {hostname}. "
            f"Affected metrics: {', '.join(sorted(affected_metrics))}. "
            f"Correlation score: {correlation_score}."
        )

        incident = Incident(
            incident_key=incident_key,
            title=title,
            status="OPEN",
            severity=severity,
            hostname=hostname,
            started_at=started_at,
            probable_cause=probable_cause,
            recommended_action=recommended_action,
            summary=summary,
            correlation_score=correlation_score,
            affected_metrics=affected_metrics,
            observation_count=1,
        )
        incident = await self.repo.create(incident)

        # Link each anomaly to this incident
        for anomaly in anomalies:
            await self.repo.link_anomaly(incident, anomaly)

        logger.info(
            "incident_created",
            incident_id=str(incident.id),
            key=incident_key,
            severity=severity,
            affected_metrics=affected_metrics,
            correlation_score=correlation_score,
        )
        return incident

    async def _update_incident(
        self,
        incident: Incident,
        anomalies: list[Anomaly],
        correlation_score: float,
        severity: str,
        affected_metrics: list[str],
    ) -> Incident:
        """Update an existing incident with new observations."""
        # Escalate severity if needed (WARNING → CRITICAL)
        if severity == "CRITICAL" and incident.severity == "WARNING":
            incident.severity = "CRITICAL"
            incident.title = build_incident_title(affected_metrics, "CRITICAL")
            logger.info(
                "incident_escalated",
                incident_id=str(incident.id),
                new_severity="CRITICAL",
            )

        # Update metadata
        incident.correlation_score = max(incident.correlation_score, correlation_score)
        incident.observation_count += 1

        # Merge affected metrics
        existing_metrics = set(incident.affected_metrics or [])
        merged = list(existing_metrics | set(affected_metrics))
        incident.affected_metrics = merged

        # Regenerate cause/recommendation with full metric set
        all_anomaly_metrics = list(set(affected_metrics) | existing_metrics)
        # Rebuild with current anomalies for updated text
        incident.probable_cause = generate_rule_based_cause(anomalies)
        incident.recommended_action = generate_rule_based_recommendation(anomalies)
        incident.summary = (
            f"Ongoing incident on {incident.hostname}. "
            f"Observed {incident.observation_count} consecutive monitoring cycles "
            f"with abnormal conditions. Affected metrics: "
            f"{', '.join(sorted(merged))}. "
            f"Correlation score: {incident.correlation_score}."
        )

        incident = await self.repo.update(incident)

        # Link new anomalies
        for anomaly in anomalies:
            await self.repo.link_anomaly(incident, anomaly)

        logger.info(
            "incident_updated",
            incident_id=str(incident.id),
            observation_count=incident.observation_count,
            severity=incident.severity,
        )
        return incident

    async def resolve_stale_incidents(
        self, hostname: str, recovery_minutes: int = 10
    ) -> int:
        """
        Resolve incidents for a host that have not been updated recently.

        Call this when a clean metric is received to close active incidents
        that are no longer being triggered.

        Returns: count of resolved incidents.
        """
        active = await self.repo.get_active_incidents()
        host_incidents = [i for i in active if i.hostname == hostname]
        resolved_count = 0

        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=recovery_minutes)
        for incident in host_incidents:
            if incident.updated_at.replace(tzinfo=timezone.utc) < cutoff:
                incident.status = "RESOLVED"
                incident.ended_at = datetime.now(tz=timezone.utc)
                await self.repo.update(incident)
                resolved_count += 1
                logger.info(
                    "incident_resolved",
                    incident_id=str(incident.id),
                    hostname=hostname,
                )

        return resolved_count

    async def get_incident(self, incident_id: uuid.UUID) -> Optional[Incident]:
        return await self.repo.get_by_id(incident_id)
