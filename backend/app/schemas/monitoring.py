"""
Unified monitoring snapshot and SSH status schemas.
Adheres strictly to preserving None for uncollected or failed metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CPUInfo(BaseModel):
    usage_percent: Optional[float] = None
    count: Optional[int] = None


class MemoryInfo(BaseModel):
    usage_percent: Optional[float] = None
    total_mb: Optional[float] = None
    used_mb: Optional[float] = None
    available_mb: Optional[float] = None


class DiskInfo(BaseModel):
    usage_percent: Optional[float] = None
    total_gb: Optional[float] = None
    used_gb: Optional[float] = None
    free_gb: Optional[float] = None


class LoadInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    load_1m: Optional[float] = Field(None, serialization_alias="1m", validation_alias="1m")
    load_5m: Optional[float] = Field(None, serialization_alias="5m", validation_alias="5m")
    load_15m: Optional[float] = Field(None, serialization_alias="15m", validation_alias="15m")


class NetworkInfo(BaseModel):
    rx_bytes: Optional[int] = None
    tx_bytes: Optional[int] = None


class ProcessItem(BaseModel):
    pid: Optional[int] = None
    name: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None


class ResponseTimeInfo(BaseModel):
    ms: Optional[float] = None
    http_status: Optional[int] = None
    enabled: bool = False
    url: Optional[str] = None


class SystemInfo(BaseModel):
    hostname: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    kernel_version: Optional[str] = None


class LogEntry(BaseModel):
    timestamp: str
    priority: str
    message: str


class DataQuality(BaseModel):
    collection_status: str = "COMPLETE"  # COMPLETE | PARTIAL | FAILED
    successful_collectors: int = 0
    failed_collectors: int = 0
    errors: List[str] = []


class UnifiedSnapshot(BaseModel):
    """
    Unified monitoring snapshot matching Section 18 of specification.
    """
    timestamp: str
    hostname: Optional[str] = None
    cpu: CPUInfo
    memory: MemoryInfo
    disk: DiskInfo
    load: LoadInfo
    network: NetworkInfo
    processes: List[ProcessItem] = []
    logs: List[LogEntry] = []
    response_time: ResponseTimeInfo
    system: SystemInfo
    collector_status: Dict[str, str] = {}
    collection_errors: List[str] = []
    data_quality: DataQuality


class SSHStatusResponse(BaseModel):
    """EC2 reachability and SSH status."""
    connected: bool
    hostname: Optional[str] = None
    timestamp: datetime
    error: Optional[str] = None
    status: str = "CONNECTED"  # CONNECTED | DEGRADED | UNAVAILABLE
