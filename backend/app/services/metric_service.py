"""
Metric service — orchestrates metric ingestion end-to-end.

This is the primary entry point called by the POST /api/metrics route handler.
It coordinates:
  1. Persisting the raw metric.
  2. Saving process snapshots.
  3. Running anomaly detection.
  4. Persisting detected anomalies.
  5. Running the incident correlation and lifecycle engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.metric import Metric, ProcessSnapshot
from app.models.anomaly import Anomaly
from app.models.incident import Incident
from app.repositories.metric_repository import MetricRepository
from app.repositories.anomaly_repository import AnomalyRepository
from app.schemas.metric import MetricIngest
from app.services.anomaly_detector import (
    build_anomaly_model,
    detect_anomalies,
)
from app.services.incident_service import IncidentService

logger = get_logger(__name__)


class MetricService:
    """Orchestrates the full metric ingestion pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.metric_repo = MetricRepository(db)
        self.anomaly_repo = AnomalyRepository(db)
        self.incident_svc = IncidentService(db)

    async def ingest(
        self, payload: MetricIngest
    ) -> tuple[Metric, list[Anomaly], Incident | None]:
        """
        Ingest a metric payload from the monitoring agent.

        Returns:
            (metric, anomalies, incident)
            - metric: the persisted Metric record
            - anomalies: list of persisted Anomaly records
            - incident: the created or updated Incident, or None if healthy
        """
        logger.info(
            "metric_ingestion_start",
            hostname=payload.hostname,
            cpu=payload.cpu_usage,
            memory=payload.memory_usage,
            disk=payload.disk_usage,
        )

        # 1. Persist metric
        metric = Metric(
            hostname=payload.hostname,
            timestamp=payload.timestamp,
            cpu_usage=payload.cpu_usage,
            memory_usage=payload.memory_usage,
            disk_usage=payload.disk_usage,
            load_1m=payload.load_1m,
            load_5m=payload.load_5m,
            load_15m=payload.load_15m,
            cpu_count=payload.cpu_count,
            memory_available_mb=payload.memory_available_mb,
            disk_free_gb=payload.disk_free_gb,
            network_rx_bytes=payload.network_rx_bytes,
            network_tx_bytes=payload.network_tx_bytes,
            response_time_ms=payload.response_time_ms,
            http_status=payload.http_status,
            os_name=payload.os_name,
            kernel_version=payload.kernel_version,
        )
        metric = await self.metric_repo.create(metric)

        # 2. Persist process snapshots
        if payload.top_cpu_process:
            cpu_snap = ProcessSnapshot(
                metric_id=metric.id,
                process_name=payload.top_cpu_process,
                pid=payload.top_cpu_pid,
                cpu_percent=payload.top_cpu_percent,
                memory_percent=None,
                snapshot_type="top_cpu",
                timestamp=payload.timestamp,
            )
            await self.metric_repo.create_process_snapshot(cpu_snap)

        if payload.top_memory_process:
            mem_snap = ProcessSnapshot(
                metric_id=metric.id,
                process_name=payload.top_memory_process,
                pid=payload.top_memory_pid,
                cpu_percent=None,
                memory_percent=payload.top_memory_percent,
                snapshot_type="top_memory",
                timestamp=payload.timestamp,
            )
            await self.metric_repo.create_process_snapshot(mem_snap)

        # 3. Run rule-based anomaly detection
        detected = detect_anomalies(payload)

        # 4. Persist anomalies
        anomaly_records: list[Anomaly] = []
        for det in detected:
            anomaly = build_anomaly_model(det, metric.id, payload.timestamp)
            anomaly = await self.anomaly_repo.create(anomaly)
            anomaly_records.append(anomaly)

        # 5. Incident correlation and lifecycle
        incident = None
        if anomaly_records:
            incident = await self.incident_svc.process_anomalies(
                hostname=payload.hostname,
                anomalies=anomaly_records,
                metric_timestamp=payload.timestamp,
            )
        else:
            # No anomalies — attempt to resolve stale incidents
            await self.incident_svc.resolve_stale_incidents(payload.hostname)

        logger.info(
            "metric_ingestion_complete",
            metric_id=str(metric.id),
            anomaly_count=len(anomaly_records),
            incident_id=str(incident.id) if incident else None,
        )

        return metric, anomaly_records, incident
