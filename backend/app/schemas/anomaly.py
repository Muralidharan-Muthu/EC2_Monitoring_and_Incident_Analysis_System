"""
Pydantic schemas for anomaly API responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnomalyResponse(BaseModel):
    """Full anomaly record returned by the API."""

    id: uuid.UUID
    metric_id: uuid.UUID
    metric_name: str
    observed_value: float
    threshold: float
    anomaly_type: str
    severity: str
    description: str
    is_persistent: bool
    consecutive_count: int
    detected_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class AnomalyListResponse(BaseModel):
    """Paginated list of anomalies."""

    anomalies: list[AnomalyResponse]
    total: int
    page: int
    page_size: int
