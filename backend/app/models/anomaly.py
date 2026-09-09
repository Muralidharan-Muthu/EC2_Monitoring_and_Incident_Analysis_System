"""
SQLAlchemy ORM model for detected anomalies.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Anomaly(Base):
    """
    Records a single detected anomaly on a specific metric observation.

    Anomalies are created by the rule-based anomaly detector.
    Multiple anomalies from the same time window are correlated
    into a single Incident by the correlation engine.
    """

    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metrics.id", ondelete="CASCADE"),
        nullable=False,
    )

    # What was detected
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "cpu_usage", "memory_usage", "disk_usage", "load"
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "threshold_exceeded", "persistent_high"

    # Severity: "WARNING" | "CRITICAL"
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Whether this anomaly persisted across multiple consecutive samples
    is_persistent: Mapped[bool] = mapped_column(default=False, nullable=False)
    consecutive_count: Mapped[int] = mapped_column(default=1, nullable=False)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    metric: Mapped["Metric"] = relationship("Metric", back_populates="anomalies")  # noqa: F821
    incident_anomalies: Mapped[list["IncidentAnomaly"]] = relationship(  # noqa: F821
        "IncidentAnomaly", back_populates="anomaly"
    )

    __table_args__ = (
        Index("ix_anomalies_metric_id", "metric_id"),
        Index("ix_anomalies_detected_at", "detected_at"),
        Index("ix_anomalies_severity", "severity"),
        Index("ix_anomalies_metric_name", "metric_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<Anomaly metric={self.metric_name} "
            f"value={self.observed_value} severity={self.severity}>"
        )
