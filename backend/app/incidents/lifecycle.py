"""
Incident lifecycle management: OPEN -> INVESTIGATING -> RESOLVED.
Tracks duration, last_seen_at, and resolution transitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from app.models.incident import Incident


def update_incident_activity(incident: Incident, timestamp: datetime) -> None:
    """Update last_seen_at on an active incident when new abnormal metrics arrive."""
    incident.last_seen_at = timestamp
    incident.updated_at = datetime.now(timezone.utc)


def resolve_incident(incident: Incident, ended_at: Optional[datetime] = None) -> None:
    """Mark an incident as RESOLVED when the host returns to healthy operating parameters."""
    end_time = ended_at or datetime.now(timezone.utc)
    incident.status = "RESOLVED"
    incident.ended_at = end_time
    incident.updated_at = end_time


def check_for_auto_resolution(
    incident: Incident,
    current_time: datetime,
    recovery_minutes: int = 10,
) -> bool:
    """
    Check if an incident has not seen any anomalies for recovery_minutes.
    If so, resolves it automatically.
    """
    if incident.status == "RESOLVED":
        return False

    ref_time = incident.last_seen_at or incident.started_at
    if ref_time is None:
        return False

    elapsed_seconds = (current_time - ref_time).total_seconds()
    if elapsed_seconds > (recovery_minutes * 60):
        resolve_incident(incident, ended_at=current_time)
        return True

    return False
