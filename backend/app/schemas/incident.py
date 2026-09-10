"""
Pydantic schemas for incidents and incident analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IncidentAnalysisSchema(BaseModel):
    """Structured analysis output stored in incident_analyses."""

    affected_metrics: list[str] = Field(default_factory=list)
    probable_causes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    analysis_source: str = "rule_based"  # "llm" | "rule_based"
    model_name: Optional[str] = None
    confidence: Optional[float] = None
    generated_at: Optional[datetime] = None
    event_relationship: Optional[str] = None

    model_config = {"from_attributes": True}


class AnomalySummary(BaseModel):
    """Lightweight anomaly summary for embedding in incident responses."""

    id: uuid.UUID
    metric_name: str
    observed_value: float
    threshold: float
    severity: str
    description: str
    is_persistent: bool
    detected_at: datetime

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    """Full incident record including embedded anomalies and analysis."""

    id: uuid.UUID
    incident_key: str
    title: str
    status: str
    severity: str
    hostname: str
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    probable_cause: Optional[str]
    recommended_action: Optional[str]
    summary: Optional[str]
    correlation_score: float
    affected_metrics: Optional[list[str]]
    llm_confidence: Optional[float]
    llm_analyzed: bool
    observation_count: int
    event_relationship: Optional[str] = None

    # Embedded related data (populated on detail endpoint)
    anomalies: list[AnomalySummary] = Field(default_factory=list)
    analysis: Optional[IncidentAnalysisSchema] = None

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""

    incidents: list[IncidentResponse]
    total: int
    page: int
    page_size: int


class IncidentUpdateRequest(BaseModel):
    """Request body for manually updating an incident's status."""

    status: str = Field(..., pattern="^(OPEN|INVESTIGATING|RESOLVED)$")
    notes: Optional[str] = None
