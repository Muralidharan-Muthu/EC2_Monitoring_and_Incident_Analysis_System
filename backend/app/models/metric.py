"""
SQLAlchemy ORM models for system metrics and process snapshots.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Metric(Base):
    """
    Stores a single system-metrics observation from a monitored host.

    Each row represents one polling cycle from the monitoring agent.
    """

    __tablename__ = "metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Core metrics
    cpu_usage: Mapped[float] = mapped_column(Float, nullable=False)
    memory_usage: Mapped[float] = mapped_column(Float, nullable=False)
    disk_usage: Mapped[float] = mapped_column(Float, nullable=False)
    load_1m: Mapped[float] = mapped_column(Float, nullable=False)
    load_5m: Mapped[float] = mapped_column(Float, nullable=False)
    load_15m: Mapped[float] = mapped_column(Float, nullable=False)

    # Supporting information
    cpu_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    memory_available_mb: Mapped[float] = mapped_column(Float, nullable=True)
    disk_free_gb: Mapped[float] = mapped_column(Float, nullable=True)

    # Network statistics
    network_rx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    network_tx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)

    # Optional response-time measurement
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # OS information
    os_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kernel_version: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    process_snapshots: Mapped[list["ProcessSnapshot"]] = relationship(
        "ProcessSnapshot", back_populates="metric", cascade="all, delete-orphan"
    )
    anomalies: Mapped[list["Anomaly"]] = relationship(  # noqa: F821
        "Anomaly", back_populates="metric", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_metrics_hostname", "hostname"),
        Index("ix_metrics_timestamp", "timestamp"),
        Index("ix_metrics_hostname_timestamp", "hostname", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<Metric id={self.id} host={self.hostname} "
            f"cpu={self.cpu_usage:.1f}% ts={self.timestamp}>"
        )


class ProcessSnapshot(Base):
    """
    Top resource-consuming process recorded alongside a metric observation.

    Captures which process was consuming the most CPU or memory at the time
    the metric was collected — used as evidence during incident analysis.
    """

    __tablename__ = "process_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metrics.id", ondelete="CASCADE"),
        nullable=False,
    )
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    snapshot_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="top_cpu"
    )  # "top_cpu" | "top_memory"
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationship
    metric: Mapped["Metric"] = relationship("Metric", back_populates="process_snapshots")

    __table_args__ = (Index("ix_process_snapshots_metric_id", "metric_id"),)

    def __repr__(self) -> str:
        return (
            f"<ProcessSnapshot process={self.process_name} "
            f"cpu={self.cpu_percent}% mem={self.memory_percent}%>"
        )
