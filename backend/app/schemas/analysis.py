"""
Pydantic schemas for LLM-generated analysis output.

These schemas validate the structured JSON returned by the Groq LLM,
ensuring the AI layer cannot inject malformed data into the database.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LLMAnalysisOutput(BaseModel):
    """
    Expected structured output from the Groq LLM.

    The LLM is instructed to return JSON matching this schema.
    If validation fails, the system falls back to rule-based analysis.
    """

    severity: str = Field(..., description="Assessed severity: WARNING or CRITICAL")
    affected_metrics: list[str] = Field(
        ..., description="List of affected metric names"
    )
    probable_cause: str = Field(
        ..., description="Evidence-based probable cause description"
    )
    evidence: list[str] = Field(
        ..., description="Observed evidence supporting the analysis"
    )
    recommended_actions: list[str] = Field(
        ..., description="Actionable remediation steps"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0"
    )
    reasoning_summary: Optional[str] = Field(
        None, description="Human-readable explanation of the reasoning chain"
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"WARNING", "CRITICAL", "NORMAL"}
        upper = v.upper()
        if upper not in allowed:
            return "WARNING"  # Safe default rather than raising
        return upper

    @field_validator("affected_metrics", "evidence", "recommended_actions", mode="before")
    @classmethod
    def ensure_list(cls, v: object) -> list:
        if isinstance(v, str):
            return [v]
        if not isinstance(v, list):
            return []
        return v


class DashboardSummary(BaseModel):
    """Summary data for the dashboard overview."""

    system_status: str  # "HEALTHY" | "DEGRADED" | "CRITICAL"
    active_incident_count: int
    highest_severity: Optional[str]
    latest_cpu: Optional[float]
    latest_memory: Optional[float]
    latest_disk: Optional[float]
    latest_load_1m: Optional[float]
    hostname: Optional[str]
    last_metric_at: Optional[str]


class TimeSeriesPoint(BaseModel):
    """Single data point in a time-series response."""

    timestamp: str
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    disk_usage: Optional[float]
    load_1m: Optional[float]
    response_time_ms: Optional[float]


class TimeSeriesResponse(BaseModel):
    """Time-series data for chart rendering."""

    data: list[TimeSeriesPoint]
    hostname: Optional[str]
    range_minutes: int
