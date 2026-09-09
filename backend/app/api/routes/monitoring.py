"""
Monitoring endpoints for EC2 reachability, on-demand metrics collection, and current status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.monitoring.snapshot_service import record_snapshot_cycle
from app.ssh.client import get_ssh_client

logger = get_logger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/status")
async def get_monitoring_status():
    """
    Check if the remote AWS EC2 instance is reachable via SSH.
    """
    ssh_client = get_ssh_client()
    status = await ssh_client.check_connection()

    state_str = "CONNECTED" if status.connected else "UNAVAILABLE"

    return {
        "success": True,
        "data": {
            "connected": status.connected,
            "hostname": status.hostname,
            "timestamp": status.timestamp if isinstance(status.timestamp, str) else status.timestamp.isoformat(),
            "status": state_str,
            "latency_ms": status.latency_ms,
            "error": status.error,
        },
        "error": None if status.connected else {
            "code": "EC2_SSH_UNAVAILABLE",
            "message": status.error or "Unable to connect to remote EC2 instance via SSH.",
        },
    }


@router.get("/current")
async def get_current_metrics(db: AsyncSession = Depends(get_db)):
    """
    Connect to EC2 via SSH, collect current metrics, run anomaly evaluation,
    persist snapshot to Supabase PostgreSQL, and return current data.
    """
    try:
        snapshot, incident = await record_snapshot_cycle(db)
        return {
            "success": True,
            "data": snapshot.model_dump(by_alias=True),
            "incident_detected": incident is not None,
            "incident_id": str(incident.id) if incident else None,
            "error": None,
        }
    except Exception as exc:
        logger.error("current_monitoring_failed", error=str(exc))
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "COLLECTION_FAILED",
                "message": "Failed to collect metrics from remote host.",
            },
        }


@router.post("/collect")
async def trigger_collection(db: AsyncSession = Depends(get_db)):
    """
    Explicitly trigger one collection cycle over SSH.
    """
    try:
        snapshot, incident = await record_snapshot_cycle(db)
        return {
            "success": True,
            "data": snapshot.model_dump(by_alias=True),
            "incident_id": str(incident.id) if incident else None,
            "error": None,
        }
    except Exception as exc:
        logger.error("trigger_collection_failed", error=str(exc))
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "MANUAL_COLLECTION_ERROR",
                "message": "Manual collection cycle encountered an error.",
            },
        }
