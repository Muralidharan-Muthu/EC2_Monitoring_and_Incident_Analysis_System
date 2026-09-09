"""
Pydantic schemas for metric API requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProcessSnapshotSchema(BaseModel):
    """Schema for a process snapshot embedded in metric payloads."""

    process_name: str = Field(..., description="Name of the process")
    pid: Optional[int] = Field(None, description="Process ID")
    cpu_percent: Optional[float] = Field(None, ge=0, le=100)
    memory_percent: Optional[float] = Field(None, ge=0, le=100)
    snapshot_type: str = Field(default="top_cpu")  # "top_cpu" | "top_memory"

    model_config = {"from_attributes": True}


class MetricIngest(BaseModel):
    """
    Payload sent by the monitoring agent to POST /api/metrics.

    All percentage fields are validated to be within [0, 100].
    """

    hostname: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime = Field(..., description="ISO 8601 timestamp (UTC)")

    # Core metrics
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    load_1m: float = Field(..., ge=0)
    load_5m: float = Field(..., ge=0)
    load_15m: float = Field(..., ge=0)

    # Supporting info
    cpu_count: int = Field(default=1, ge=1)
    memory_available_mb: Optional[float] = Field(None, ge=0)
    disk_free_gb: Optional[float] = Field(None, ge=0)

    # Network
    network_rx_bytes: Optional[int] = Field(None, ge=0)
    network_tx_bytes: Optional[int] = Field(None, ge=0)

    # Application health (optional)
    response_time_ms: Optional[float] = Field(None, ge=0)
    http_status: Optional[int] = Field(None)

    # Process info (embedded directly in the agent payload)
    top_cpu_process: Optional[str] = Field(None)
    top_cpu_percent: Optional[float] = Field(None, ge=0, le=100)
    top_memory_process: Optional[str] = Field(None)
    top_memory_percent: Optional[float] = Field(None, ge=0, le=100)
    top_cpu_pid: Optional[int] = None
    top_memory_pid: Optional[int] = None

    # OS information
    os_name: Optional[str] = Field(None, max_length=255)
    kernel_version: Optional[str] = Field(None, max_length=255)

    @field_validator("cpu_usage", "memory_usage", "disk_usage", mode="before")
    @classmethod
    def clamp_percent(cls, v: float) -> float:
        """Clamp percentage values to [0, 100] to handle edge cases."""
        return max(0.0, min(100.0, float(v)))


class MetricResponse(BaseModel):
    """Full metric record returned by the API."""

    id: uuid.UUID
    hostname: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    load_1m: float
    load_5m: float
    load_15m: float
    cpu_count: int
    memory_available_mb: Optional[float]
    disk_free_gb: Optional[float]
    network_rx_bytes: Optional[int]
    network_tx_bytes: Optional[int]
    response_time_ms: Optional[float]
    http_status: Optional[int]
    os_name: Optional[str]
    kernel_version: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricIngestResponse(BaseModel):
    """Response returned after successful metric ingestion."""

    metric_id: uuid.UUID
    anomalies_detected: int
    incident_id: Optional[uuid.UUID] = None
    message: str = "Metric ingested successfully"
