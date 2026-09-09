"""
Persistence tracker for metric anomalies.

Prevents transient spikes from creating noisy critical incidents.
Tracks consecutive samples above threshold before flagging an anomaly as persistent.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Tuple

# Key: (hostname, metric_name) -> consecutive abnormal count
_consecutive_counts: dict[Tuple[str, str], int] = defaultdict(int)


def record_violation(hostname: str, metric_name: str, required_samples: int = 3) -> tuple[int, bool]:
    """
    Increment consecutive violation count and return (count, is_persistent).
    """
    key = (hostname, metric_name)
    _consecutive_counts[key] += 1
    count = _consecutive_counts[key]
    is_persistent = count >= required_samples
    return count, is_persistent


def reset_persistence(hostname: str, metric_name: str) -> None:
    """Reset violation count when a metric returns to normal."""
    key = (hostname, metric_name)
    _consecutive_counts.pop(key, None)


def get_violation_count(hostname: str, metric_name: str) -> int:
    """Return the current consecutive count for a metric."""
    return _consecutive_counts.get((hostname, metric_name), 0)


def clear_all_persistence() -> None:
    """Clear all in-memory persistence counts (useful for testing)."""
    _consecutive_counts.clear()
