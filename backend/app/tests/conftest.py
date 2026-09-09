"""pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.services.anomaly_detector import _consecutive_counts


@pytest.fixture(autouse=True)
def clear_persistence_state():
    """Clear the in-memory persistence state before each test."""
    _consecutive_counts.clear()
    yield
    _consecutive_counts.clear()


@pytest.fixture
def sample_timestamp() -> datetime:
    return datetime.now(tz=timezone.utc)
