"""
Pydantic schemas for metric API requests and responses.
Strictly preserves None for any uncollected or failed metrics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class ProcessSnapshotSchema(BaseModel):
    """Schema for a process snapshot associated with a metric snapshot."""

    id: Optional[uuid.UUID] = None
    pid: Optional[int] = Field(None, description="Process ID")
    process_name: str = Field(..., description="Name of the process")
    cpu_percent: Optional[float] = Field(None, ge=0)
    memory_percent: Optional[float] = Field(None, ge=0)
    snapshot_type: Optional[str] = Field(default="top_process")

    model_config = {"from_attributes": True}


class MetricIngest(BaseModel):
    """
    Payload for metric ingestion. All metric measurements are nullable.
    """

    hostname: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime = Field(..., description="ISO 8601 timestamp (UTC)")

    # Core metrics (nullable — None means failed/unavailable)
    cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, ge=0, le=100)
    disk_usage: Optional[float] = Field(None, ge=0, le=100)
    load_1m: Optional[float] = Field(None, ge=0)
    load_5m: Optional[float] = Field(None, ge=0)
    load_15m: Optional[float] = Field(None, ge=0)

    # Supporting info
    cpu_count: Optional[int] = Field(None, ge=1)
    memory_total_mb: Optional[float] = Field(None, ge=0)
    memory_used_mb: Optional[float] = Field(None, ge=0)
    memory_available_mb: Optional[float] = Field(None, ge=0)
    disk_total_gb: Optional[float] = Field(None, ge=0)
    disk_used_gb: Optional[float] = Field(None, ge=0)
    disk_free_gb: Optional[float] = Field(None, ge=0)

    # Network
    network_rx_bytes: Optional[int] = Field(None, ge=0)
    network_tx_bytes: Optional[int] = Field(None, ge=0)

    # Application health (optional)
    response_time_ms: Optional[float] = Field(None, ge=0)
    http_status: Optional[int] = Field(None)

    # Process info
    top_cpu_process: Optional[str] = Field(None)
    top_cpu_percent: Optional[float] = Field(None, ge=0, le=100)
    top_memory_process: Optional[str] = Field(None)
    top_memory_percent: Optional[float] = Field(None, ge=0, le=100)
    top_cpu_pid: Optional[int] = None
    top_memory_pid: Optional[int] = None
    processes: Optional[List[ProcessSnapshotSchema]] = None

    # OS information
    os_name: Optional[str] = Field(None, max_length=255)
    kernel_version: Optional[str] = Field(None, max_length=255)

    @field_validator("cpu_usage", "memory_usage", "disk_usage", mode="before")
    @classmethod
    def clamp_percent(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        return max(0.0, min(100.0, float(v)))


class MetricResponse(BaseModel):
    """Full metric record returned by the API. Preserves None for missing data."""

    id: uuid.UUID
    hostname: str
    timestamp: datetime
    cpu_usage: Optional[float] = None
    cpu_count: Optional[int] = None
    memory_usage: Optional[float] = None
    memory_total_mb: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_available_mb: Optional[float] = None
    disk_usage: Optional[float] = None
    disk_total_gb: Optional[float] = None
    disk_used_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    load_1m: Optional[float] = None
    load_5m: Optional[float] = None
    load_15m: Optional[float] = None
    network_rx_bytes: Optional[int] = None
    network_tx_bytes: Optional[int] = None
    response_time_ms: Optional[float] = None
    http_status: Optional[int] = None
    os_name: Optional[str] = None
    kernel_version: Optional[str] = None
    created_at: datetime
    processes: Optional[List[ProcessSnapshotSchema]] = None

    model_config = {"from_attributes": True}


class MetricIngestResponse(BaseModel):
    """Response returned after successful metric ingestion."""

    metric_id: uuid.UUID
    anomalies_detected: int
    incident_id: Optional[uuid.UUID] = None
    message: str = "Metric ingested successfully"
