"""
Unit tests for the correlation engine.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.services.correlation_engine import (
    compute_correlation_score,
    compute_incident_key,
    determine_severity,
    build_incident_title,
    generate_rule_based_cause,
    METRIC_WEIGHTS,
)


def make_anomaly(metric_name: str, severity: str = "CRITICAL", is_persistent: bool = False):
    """Create a mock Anomaly object."""
    a = MagicMock()
    a.metric_name = metric_name
    a.severity = severity
    a.is_persistent = is_persistent
    return a


class TestCorrelationScore:
    def test_single_cpu_anomaly(self):
        anomalies = [make_anomaly("cpu_usage")]
        score = compute_correlation_score(anomalies)
        assert score == METRIC_WEIGHTS["cpu_usage"]

    def test_cpu_memory_load_saturation(self):
        """Scenario 4 resources: CPU+Memory+Load+Disk should yield high score."""
        anomalies = [
            make_anomaly("cpu_usage"),
            make_anomaly("memory_usage"),
            make_anomaly("load_1m"),
            make_anomaly("disk_usage"),
        ]
        score = compute_correlation_score(anomalies)
        expected = (
            METRIC_WEIGHTS["cpu_usage"]
            + METRIC_WEIGHTS["memory_usage"]
            + METRIC_WEIGHTS["load_1m"]
            + METRIC_WEIGHTS["disk_usage"]
        )
        assert score == expected

    def test_persistent_anomaly_adds_bonus(self):
        """Persistent anomalies should increase the score."""
        non_persistent = [make_anomaly("cpu_usage", is_persistent=False)]
        persistent = [make_anomaly("cpu_usage", is_persistent=True)]

        assert compute_correlation_score(persistent) > compute_correlation_score(non_persistent)

    def test_empty_anomalies(self):
        assert compute_correlation_score([]) == 0.0


class TestIncidentKey:
    def test_same_metrics_same_key(self):
        key1 = compute_incident_key("host-1", ["cpu_usage", "memory_usage"])
        key2 = compute_incident_key("host-1", ["memory_usage", "cpu_usage"])
        assert key1 == key2, "Order of metrics should not affect the key"

    def test_different_hostname_different_key(self):
        key1 = compute_incident_key("host-1", ["cpu_usage"])
        key2 = compute_incident_key("host-2", ["cpu_usage"])
        assert key1 != key2

    def test_different_metrics_different_key(self):
        key1 = compute_incident_key("host", ["cpu_usage"])
        key2 = compute_incident_key("host", ["memory_usage"])
        assert key1 != key2

    def test_key_is_32_chars(self):
        key = compute_incident_key("host", ["cpu_usage"])
        assert len(key) == 32


class TestSeverityDetermination:
    def test_critical_wins(self):
        anomalies = [
            make_anomaly("cpu_usage", severity="WARNING"),
            make_anomaly("memory_usage", severity="CRITICAL"),
        ]
        assert determine_severity(anomalies) == "CRITICAL"

    def test_all_warning_stays_warning(self):
        anomalies = [
            make_anomaly("cpu_usage", severity="WARNING"),
            make_anomaly("disk_usage", severity="WARNING"),
        ]
        assert determine_severity(anomalies) == "WARNING"

    def test_single_critical(self):
        anomalies = [make_anomaly("cpu_usage", severity="CRITICAL")]
        assert determine_severity(anomalies) == "CRITICAL"


class TestRuleBasedCause:
    def test_cpu_and_load_pattern(self):
        anomalies = [make_anomaly("cpu_usage"), make_anomaly("load_1m")]
        cause = generate_rule_based_cause(anomalies)
        assert "CPU" in cause or "cpu" in cause.lower()
        assert "Probable cause" in cause or "probable" in cause.lower()

    def test_disk_only_pattern(self):
        anomalies = [make_anomaly("disk_usage")]
        cause = generate_rule_based_cause(anomalies)
        assert "disk" in cause.lower() or "Disk" in cause

    def test_full_saturation_pattern(self):
        anomalies = [
            make_anomaly("cpu_usage"),
            make_anomaly("memory_usage"),
            make_anomaly("load_1m"),
            make_anomaly("disk_usage"),
            make_anomaly("response_time_ms"),
        ]
        cause = generate_rule_based_cause(anomalies)
        assert cause  # Should produce some output
        assert "saturation" in cause.lower() or "resource" in cause.lower()
