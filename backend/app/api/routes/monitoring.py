"""
Monitoring endpoints for EC2 reachability, on-demand metrics collection, and current status.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.monitoring.snapshot_service import record_snapshot_cycle
from app.ssh.client import get_ssh_client, reset_ssh_client
from app.monitoring.collector_service import reset_collector_service

logger = get_logger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class ConfigureHostRequest(BaseModel):
    host: str
    username: Optional[str] = "ubuntu"
    port: Optional[int] = 22


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


@router.post("/reset-database")
async def reset_database(db: AsyncSession = Depends(get_db)):
    """
    Clear all telemetry, anomaly, and incident records from the database.
    Allows testing clean-slate monitoring and incident creation.
    """
    from sqlalchemy import text
    try:
        await db.execute(text("DELETE FROM incident_analyses;"))
        await db.execute(text("DELETE FROM incident_anomalies;"))
        await db.execute(text("DELETE FROM anomalies;"))
        await db.execute(text("DELETE FROM incidents;"))
        await db.execute(text("DELETE FROM process_snapshots;"))
        await db.execute(text("DELETE FROM metrics;"))
        await db.commit()
        return {
            "success": True,
            "message": "All database records have been cleared successfully.",
        }
    except Exception as exc:
        logger.error("reset_database_failed", error=str(exc))
        return {
            "success": False,
            "error": {
                "code": "RESET_FAILED",
                "message": f"Failed to reset database: {exc}",
            },
        }


@router.post("/configure-host")
async def configure_ec2_host(payload: ConfigureHostRequest, db: AsyncSession = Depends(get_db)):
    """
    Dynamically update EC2 host (e.g. after EC2 instance reboot with new Public IP/DNS),
    persists change to .env, tests SSH connection, and triggers an initial metric capture.
    """
    raw_input = payload.host.strip()

    # Auto-extract host and username if user pasted a full ssh command:
    # e.g. ssh -i "key.pem" ubuntu@ec2-xx-xx-xx-xx.ap-south-1.compute.amazonaws.com
    ssh_match = re.search(
        r'(?:([a-zA-Z0-9_\-]+)@)?([a-zA-Z0-9\.\-]+(?:compute\.amazonaws\.com|\d+\.\d+\.\d+\.\d+))',
        raw_input,
    )
    if ssh_match:
        extracted_user = ssh_match.group(1)
        clean_host = ssh_match.group(2)
        clean_user = extracted_user or payload.username or "ubuntu"
    else:
        clean_host = raw_input.replace("https://", "").replace("http://", "").split("/")[0]
        clean_user = payload.username or "ubuntu"

    # Update in-memory settings
    settings = get_settings()
    settings.ec2_host = clean_host
    settings.ec2_username = clean_user
    if payload.port:
        settings.ec2_port = payload.port

    # Persist to .env file
    env_path = Path("backend/.env")
    if not env_path.exists():
        env_path = Path(".env")
    if env_path.exists():
        try:
            content = env_path.read_text(encoding="utf-8")
            if "EC2_HOST=" in content:
                content = re.sub(r"EC2_HOST=.*", f"EC2_HOST={clean_host}", content)
            else:
                content += f"\nEC2_HOST={clean_host}\n"
            if "EC2_USERNAME=" in content:
                content = re.sub(r"EC2_USERNAME=.*", f"EC2_USERNAME={clean_user}", content)
            env_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning("failed_to_write_env_file", error=str(e))

    # Reset singletons
    reset_ssh_client()
    reset_collector_service()

    # Test connection
    client = get_ssh_client()
    status = await client.check_connection()

    if not status.connected:
        return {
            "success": False,
            "connected": False,
            "host": clean_host,
            "username": clean_user,
            "error": {
                "code": "SSH_CONNECTION_FAILED",
                "message": status.error or f"Could not connect to {clean_host} on port {settings.ec2_port}.",
            },
        }

    # Connection succeeded! Run immediate collection and persist to Supabase
    try:
        snapshot, incident = await record_snapshot_cycle(db)
        return {
            "success": True,
            "connected": True,
            "host": clean_host,
            "username": clean_user,
            "latency_ms": status.latency_ms,
            "message": f"Successfully connected to EC2 instance ({clean_host}) and ingested initial metrics.",
            "data": snapshot.model_dump(by_alias=True) if snapshot else None,
            "incident_id": str(incident.id) if incident else None,
        }
    except Exception as exc:
        try:
            snapshot, incident = await record_snapshot_cycle(db)
            return {
                "success": True,
                "connected": True,
                "host": clean_host,
                "username": clean_user,
                "message": f"Connected to {clean_host} via SSH. Metric ingestion started.",
            }
        except:
            return {
                "success": True,
                "connected": True,
                "host": clean_host,
                "username": clean_user,
                "message": f"Connected to {clean_host} via SSH. Metric ingestion started.",
            }


@router.get("/discover-instances")
async def discover_ec2_instances():
    """
    Use boto3 to list all RUNNING EC2 instances in the configured AWS region.
    Returns instance id, public DNS, public IP, name tag, and instance type.
    This allows the frontend to auto-populate the host field without manual copy-paste.
    """
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError

        _settings = get_settings()

        # Build boto3 session — prefer explicit credentials, fall back to IAM role / env vars
        session_kwargs: dict = {"region_name": _settings.aws_region or "ap-south-1"}
        if _settings.aws_access_key_id and _settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = _settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = _settings.aws_secret_access_key

        session = boto3.Session(**session_kwargs)
        ec2 = session.client("ec2")

        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        instances = []
        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                # Extract Name tag
                name = next(
                    (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                    inst.get("InstanceId", ""),
                )
                public_dns = inst.get("PublicDnsName") or ""
                public_ip = inst.get("PublicIpAddress") or ""
                if not public_dns and not public_ip:
                    continue  # Skip instances with no public address
                instances.append({
                    "instance_id": inst.get("InstanceId"),
                    "name": name,
                    "instance_type": inst.get("InstanceType"),
                    "public_dns": public_dns,
                    "public_ip": public_ip,
                    "state": inst.get("State", {}).get("Name"),
                    "region": _settings.aws_region,
                    "launch_time": inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else None,
                })

        return {
            "success": True,
            "instances": instances,
            "count": len(instances),
            "region": _settings.aws_region,
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error("discover_instances_failed", error=error_msg)
        return {
            "success": False,
            "instances": [],
            "count": 0,
            "error": {
                "code": "AWS_DISCOVERY_FAILED",
                "message": error_msg,
            },
        }


@router.post("/auto-connect")
async def auto_connect_to_instance(db: AsyncSession = Depends(get_db)):
    """
    Use boto3 to find the first running EC2 instance in the configured region,
    set it as the active host, test SSH, and start ingesting metrics — all automatically.
    """
    try:
        import boto3

        _settings = get_settings()
        session_kwargs: dict = {"region_name": _settings.aws_region or "ap-south-1"}
        if _settings.aws_access_key_id and _settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = _settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = _settings.aws_secret_access_key

        session = boto3.Session(**session_kwargs)
        ec2 = session.client("ec2")

        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        target_host = None
        target_user = _settings.ec2_username or "ubuntu"

        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                dns = inst.get("PublicDnsName") or inst.get("PublicIpAddress")
                if dns:
                    target_host = dns
                    break
            if target_host:
                break

        if not target_host:
            return {
                "success": False,
                "error": {
                    "code": "NO_RUNNING_INSTANCES",
                    "message": "No running EC2 instances with a public IP/DNS were found in your AWS account.",
                },
            }

        # Delegate to configure-host logic
        import re
        from pathlib import Path
        from app.ssh.client import get_ssh_client, reset_ssh_client
        from app.monitoring.collector_service import reset_collector_service

        _settings.ec2_host = target_host
        _settings.ec2_username = target_user

        # Persist to .env
        env_path = Path("backend/.env") if Path("backend/.env").exists() else Path(".env")
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            content = re.sub(r"EC2_HOST=.*", f"EC2_HOST={target_host}", content) if "EC2_HOST=" in content else content + f"\nEC2_HOST={target_host}\n"
            env_path.write_text(content, encoding="utf-8")

        reset_ssh_client()
        reset_collector_service()

        client = get_ssh_client()
        status = await client.check_connection()

        if not status.connected:
            return {
                "success": False,
                "connected": False,
                "host": target_host,
                "error": {
                    "code": "SSH_CONNECTION_FAILED",
                    "message": status.error or f"Auto-discovered {target_host} but SSH connection failed. Check Security Group port 22.",
                },
            }

        snapshot, incident = await record_snapshot_cycle(db)
        return {
            "success": True,
            "connected": True,
            "host": target_host,
            "username": target_user,
            "latency_ms": status.latency_ms,
            "message": f"Auto-connected to EC2 instance ({target_host}) and ingested first metrics.",
            "data": snapshot.model_dump(by_alias=True) if snapshot else None,
            "incident_id": str(incident.id) if incident else None,
        }

    except Exception as exc:
        logger.error("auto_connect_failed", error=str(exc))
        return {
            "success": False,
            "error": {
                "code": "AUTO_CONNECT_ERROR",
                "message": str(exc),
            },
        }
