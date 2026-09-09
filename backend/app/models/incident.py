"""
SQLAlchemy ORM models for incidents and incident analysis.

An Incident represents a correlated set of anomalies that were observed
within the same time window. The system ensures deduplication: the same
ongoing condition updates one incident rather than creating new ones.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Incident(Base):
    """
    Represents a correlated incident — one or more related anomalies
    grouped by the correlation engine into a single actionable event.
    """

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Unique key used for deduplication.
    # Derived from: hostname + affected metric names (sorted) + date bucket.
    incident_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # Status: "OPEN" | "INVESTIGATING" | "RESOLVED"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    # Severity: "WARNING" | "CRITICAL"
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    hostname: Mapped[str] = mapped_column(String(255), nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Rule-based analysis (always populated, regardless of LLM availability)
    probable_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Correlation metadata
    correlation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    affected_metrics: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # LLM-generated analysis (populated after POST /analyze)
    llm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_analyzed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Observation count — incremented each monitoring cycle
    observation_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    incident_anomalies: Mapped[list["IncidentAnomaly"]] = relationship(
        "IncidentAnomaly", back_populates="incident", cascade="all, delete-orphan"
    )
    analysis: Mapped["IncidentAnalysis | None"] = relationship(
        "IncidentAnalysis", back_populates="incident", uselist=False
    )

    __table_args__ = (
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_hostname", "hostname"),
        Index("ix_incidents_started_at", "started_at"),
        Index("ix_incidents_incident_key", "incident_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<Incident id={self.id} title={self.title!r} "
            f"severity={self.severity} status={self.status}>"
        )


class IncidentAnomaly(Base):
    """
    Many-to-many join table between Incident and Anomaly.

    Tracks which anomalies were correlated into which incident.
    """

    __tablename__ = "incident_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    anomaly_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("anomalies.id", ondelete="CASCADE"),
        nullable=False,
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    incident: Mapped["Incident"] = relationship(
        "Incident", back_populates="incident_anomalies"
    )
    anomaly: Mapped["Anomaly"] = relationship(
        "Anomaly", back_populates="incident_anomalies"
    )

    __table_args__ = (
        Index("ix_incident_anomalies_incident_id", "incident_id"),
        Index("ix_incident_anomalies_anomaly_id", "anomaly_id"),
    )


class IncidentAnalysis(Base):
    """
    Stores the structured analysis output produced by the LangGraph workflow.

    One-to-one relationship with Incident.
    If the LLM is unavailable, the fallback rule-based analysis is stored here.
    """

    __tablename__ = "incident_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Structured analysis fields (stored as JSONB for flexibility)
    affected_metrics: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    probable_causes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    recommended_actions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source: "llm" | "rule_based"
    analysis_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="rule_based"
    )
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Raw LLM response for debugging (sanitised — no secrets)
    raw_llm_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    incident: Mapped["Incident"] = relationship("Incident", back_populates="analysis")

    __table_args__ = (Index("ix_incident_analyses_incident_id", "incident_id"),)

    def __repr__(self) -> str:
        return (
            f"<IncidentAnalysis incident_id={self.incident_id} "
            f"source={self.analysis_source}>"
        )
