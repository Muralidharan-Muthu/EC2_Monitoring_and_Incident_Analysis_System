"""
Incident Service managing correlation, deduplication, and database persistence.
Ensures continuing abnormal conditions update the existing incident rather than duplicating.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.incidents.correlation import (
    build_incident_title,
    compute_correlation_score,
    compute_incident_key,
    generate_rule_based_cause,
    generate_rule_based_recommendation,
    generate_rule_based_summary,
)
from app.incidents.lifecycle import check_for_auto_resolution, update_incident_activity
from app.incidents.severity import determine_severity
from app.models.anomaly import Anomaly
from app.models.incident import Incident, IncidentAnomaly

logger = get_logger(__name__)


async def correlate_and_persist_incident(
    db: AsyncSession,
    hostname: str,
    anomalies: List[Anomaly],
    timestamp: datetime,
    processes: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Incident]:
    """
    Correlate a list of newly detected anomalies into an incident.

    If an active incident already exists for this host/condition, it is updated.
    If no anomalies are present, checks for auto-resolution of active incidents.
    """
    settings = get_settings()

    # 1. Handle normal state (no anomalies)
    if not anomalies:
        # Check active incidents for auto-resolution
        stmt = select(Incident).where(
            Incident.status.in_(["OPEN", "INVESTIGATING"]),
        )
        res = await db.execute(stmt)
        active_incidents = res.scalars().all()
        for inc in active_incidents:
            if check_for_auto_resolution(inc, timestamp, recovery_minutes=settings.correlation_window_minutes * 2):
                logger.info("incident_auto_resolved", incident_id=str(inc.id))
        return None

    # 2. Extract metrics and calculate attributes
    affected_metrics = sorted(list({a.metric_name for a in anomalies}))
    incident_key = compute_incident_key(hostname, affected_metrics)
    batch_severity = determine_severity(anomalies)
    batch_score = compute_correlation_score(anomalies)
    title = build_incident_title(affected_metrics, batch_severity)
    cause = generate_rule_based_cause(anomalies, processes)
    recs = generate_rule_based_recommendation(anomalies)
    summary = generate_rule_based_summary(anomalies, batch_severity, hostname)

    # 3. Look for existing open incident with matching key or host
    stmt = (
        select(Incident)
        .where(
            Incident.status.in_(["OPEN", "INVESTIGATING"]),
            Incident.incident_key == incident_key,
        )
        .order_by(Incident.started_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    existing_incident = res.scalar_one_or_none()

    # If no key match, check for any open incident on this host within the correlation window
    if not existing_incident:
        stmt_host = (
            select(Incident)
            .where(Incident.status.in_(["OPEN", "INVESTIGATING"]))
            .order_by(Incident.started_at.desc())
            .limit(1)
        )
        res_host = await db.execute(stmt_host)
        cand = res_host.scalar_one_or_none()
        if cand:
            delta_mins = abs((timestamp - (cand.last_seen_at or cand.started_at)).total_seconds()) / 60.0
            if delta_mins <= settings.correlation_window_minutes:
                existing_incident = cand

    if existing_incident:
        # Update existing incident (Deduplication!)
        update_incident_activity(existing_incident, timestamp)

        # Upgrade severity if necessary (CRITICAL > HIGH > MEDIUM > LOW)
        sev_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        if sev_rank.get(batch_severity, 0) > sev_rank.get(existing_incident.severity, 0):
            existing_incident.severity = batch_severity
            existing_incident.title = title

        # Keep highest correlation score
        existing_incident.correlation_score = max(existing_incident.correlation_score or 0.0, batch_score)
        existing_incident.probable_cause = cause
        existing_incident.recommended_action = recs
        existing_incident.summary = summary

        # Link new anomalies
        for a in anomalies:
            link = IncidentAnomaly(incident_id=existing_incident.id, anomaly_id=a.id)
            db.add(link)

        await db.flush()
        logger.info(
            "incident_updated",
            incident_id=str(existing_incident.id),
            key=incident_key,
            severity=existing_incident.severity,
        )
        return existing_incident

    # 4. Create new incident
    new_incident = Incident(
        id=uuid.uuid4(),
        incident_key=incident_key,
        title=title,
        status="OPEN",
        severity=batch_severity,
        correlation_score=batch_score,
        started_at=timestamp,
        last_seen_at=timestamp,
        probable_cause=cause,
        recommended_action=recs,
        summary=summary,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_incident)
    await db.flush()

    # Link anomalies
    for a in anomalies:
        link = IncidentAnomaly(incident_id=new_incident.id, anomaly_id=a.id)
        db.add(link)

    await db.flush()
    logger.info(
        "incident_created",
        incident_id=str(new_incident.id),
        key=incident_key,
        severity=batch_severity,
    )
    return new_incident
