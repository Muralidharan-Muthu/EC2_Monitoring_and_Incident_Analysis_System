"""
FastAPI application entry point.

Assembles all routes, configures middleware, runs environment validation,
and manages background periodic SSH metric collection in the lifespan.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import anomalies, dashboard, health, incidents, metrics, monitoring
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger
from app.monitoring.snapshot_service import record_snapshot_cycle

# Configure structured logging before anything else
configure_logging()
logger = get_logger(__name__)
settings = get_settings()


def _discover_ec2_host_via_boto3() -> str | None:
    """
    Use boto3 to find the first running EC2 instance's public DNS in the
    configured AWS region. Called at startup when EC2_HOST is not set in .env.
    Returns the public DNS/IP string, or None if none found or credentials missing.
    """
    try:
        import boto3  # type: ignore

        session_kwargs: dict = {"region_name": settings.aws_region or "ap-south-1"}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        session = boto3.Session(**session_kwargs)
        ec2 = session.client("ec2")
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                dns = inst.get("PublicDnsName") or inst.get("PublicIpAddress")
                if dns:
                    logger.info(
                        "ec2_host_auto_discovered",
                        instance_id=inst.get("InstanceId"),
                        host=dns,
                        region=settings.aws_region,
                    )
                    return dns
        logger.warning("ec2_auto_discovery_no_running_instances", region=settings.aws_region)
        return None
    except Exception as exc:
        logger.warning("ec2_auto_discovery_failed", error=str(exc))
        return None


async def _periodic_monitoring_loop(stop_event: asyncio.Event) -> None:
    """
    Background worker that runs every COLLECTION_INTERVAL_SECONDS.
    Performs agentless remote monitoring over SSH.
    """
    logger.info(
        "periodic_monitoring_started",
        interval_seconds=settings.collection_interval_seconds,
        host=settings.ec2_host,
    )

    # Initial brief pause to let server bind ports cleanly
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=2.0)
        return
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as session:
                snapshot, incident = await record_snapshot_cycle(session)
                logger.info(
                    "periodic_collection_complete",
                    quality=snapshot.data_quality.collection_status,
                    cpu=snapshot.cpu.usage_percent,
                    memory=snapshot.memory.usage_percent,
                    incident_active=incident is not None,
                )
        except Exception as exc:
            logger.warning("periodic_collection_cycle_error", error=str(exc))

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=float(settings.collection_interval_seconds),
            )
            break
        except asyncio.TimeoutError:
            continue

    logger.info("periodic_monitoring_stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(
        "application_startup",
        name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        ec2_host=settings.ec2_host,
    )

    # Validate SSH private key file existence
    valid_key, key_msg = settings.validate_ssh_key()
    if not valid_key:
        logger.error("ssh_key_validation_warning", detail=key_msg)
    else:
        logger.info("ssh_key_validated", detail=key_msg)

    # ---- Auto-discover EC2 host via boto3 if not explicitly set ----
    if not settings.ec2_host and (settings.aws_access_key_id or settings.aws_region):
        discovered = _discover_ec2_host_via_boto3()
        if discovered:
            settings.ec2_host = discovered
            # Persist discovered host to .env so it survives hot-reload
            import re
            from pathlib import Path
            for candidate in (Path("backend/.env"), Path(".env")):
                if candidate.exists():
                    content = candidate.read_text(encoding="utf-8")
                    if "EC2_HOST=" in content:
                        content = re.sub(r"EC2_HOST=.*", f"EC2_HOST={discovered}", content)
                    else:
                        content += f"\nEC2_HOST={discovered}\n"
                    candidate.write_text(content, encoding="utf-8")
                    break

    # Start background SSH collection loop if EC2_HOST is now known
    stop_event = asyncio.Event()
    bg_task = None
    if settings.ec2_host and settings.ec2_private_key_path:
        bg_task = asyncio.create_task(_periodic_monitoring_loop(stop_event))

    yield

    # Shutdown
    if bg_task:
        stop_event.set()
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass

    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """
    Application factory.
    Returns a configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "EC2 Monitoring and Incident Analysis System — "
            "remote SSH Linux system metrics, anomaly detection, "
            "incident correlation, and LangGraph-powered AI analysis."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    api_prefix = "/api"

    app.include_router(health.router, prefix=api_prefix)
    app.include_router(monitoring.router, prefix=api_prefix)
    app.include_router(metrics.router, prefix=api_prefix)
    app.include_router(anomalies.router, prefix=api_prefix)
    app.include_router(incidents.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)

    return app


app = create_app()
