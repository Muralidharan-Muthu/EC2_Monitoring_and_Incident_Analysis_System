"""
Snapshot service: orchestrates collection, metric storage, anomaly detection,
and incident correlation into Supabase PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomaly.detector import build_anomaly_model, detect_anomalies
from app.core.logging import get_logger
from app.incidents.incident_service import correlate_and_persist_incident
from app.models.incident import Incident
from app.models.metric import MetricSnapshot
from app.models.process_snapshot import ProcessSnapshot
from app.monitoring.collector_service import get_collector_service
from app.schemas.monitoring import UnifiedSnapshot

logger = get_logger(__name__)


async def record_snapshot_cycle(
    db: AsyncSession,
) -> Tuple[UnifiedSnapshot, Optional[Incident]]:
    """
    Execute one complete monitoring and analysis cycle:
    1. Collect UnifiedSnapshot from EC2 via SSH
    2. Persist MetricSnapshot & ProcessSnapshot to DB
    3. Run deterministic anomaly detection
    4. Persist detected anomalies
    5. Run correlation engine & update/create incidents
    """
    collector = get_collector_service()
    snapshot: UnifiedSnapshot = await collector.collect_snapshot()

    now_utc = datetime.now(timezone.utc)
    snapshot_id = uuid.uuid4()

    # 1. Create DB MetricSnapshot
    metric_record = MetricSnapshot(
        id=snapshot_id,
        timestamp=now_utc,
        hostname=snapshot.hostname or "unknown",
        cpu_usage=snapshot.cpu.usage_percent,
        cpu_count=snapshot.cpu.count,
        memory_usage=snapshot.memory.usage_percent,
        memory_total_mb=snapshot.memory.total_mb,
        memory_used_mb=snapshot.memory.used_mb,
        memory_available_mb=snapshot.memory.available_mb,
        disk_usage=snapshot.disk.usage_percent,
        disk_total_gb=snapshot.disk.total_gb,
        disk_used_gb=snapshot.disk.used_gb,
        disk_free_gb=snapshot.disk.free_gb,
        load_1m=snapshot.load.load_1m,
        load_5m=snapshot.load.load_5m,
        load_15m=snapshot.load.load_15m,
        network_rx_bytes=snapshot.network.rx_bytes,
        network_tx_bytes=snapshot.network.tx_bytes,
        response_time_ms=snapshot.response_time.ms,
        http_status=snapshot.response_time.http_status,
        os_name=snapshot.system.os_name,
        kernel_version=snapshot.system.kernel_version,
        created_at=now_utc,
    )
    db.add(metric_record)

    # 2. Add ProcessSnapshots
    process_dicts = []
    for proc in snapshot.processes:
        p_row = ProcessSnapshot(
            id=uuid.uuid4(),
            metric_id=snapshot_id,
            pid=proc.pid,
            process_name=proc.name,
            cpu_percent=proc.cpu_percent,
            memory_percent=proc.memory_percent,
            snapshot_type="top_process",
            timestamp=now_utc,
        )
        db.add(p_row)
        process_dicts.append(proc.model_dump())

    await db.flush()

    # 3. Detect anomalies deterministically
    detected = detect_anomalies(
        hostname=snapshot.hostname or "unknown",
        cpu_usage=snapshot.cpu.usage_percent,
        cpu_count=snapshot.cpu.count,
        memory_usage=snapshot.memory.usage_percent,
        disk_usage=snapshot.disk.usage_percent,
        load_1m=snapshot.load.load_1m,
        response_time_ms=snapshot.response_time.ms,
    )

    persisted_anomalies = []
    for det in detected:
        anom_row = build_anomaly_model(det, metric_id=snapshot_id, timestamp=now_utc)
        db.add(anom_row)
        persisted_anomalies.append(anom_row)

    if persisted_anomalies:
        await db.flush()

    # 4. Correlate and manage incidents
    incident = await correlate_and_persist_incident(
        db=db,
        hostname=snapshot.hostname or "unknown",
        anomalies=persisted_anomalies,
        timestamp=now_utc,
        processes=process_dicts,
    )

    await db.commit()
    return snapshot, incident
