"""
Unit tests for the anomaly detector.

Tests cover:
  - Normal values (no anomaly)
  - CPU warning threshold
  - CPU critical threshold
  - Memory warning threshold
  - Memory critical threshold
  - Disk warning/critical
  - System load thresholds
  - Persistence tracking (N consecutive samples)
  - Persistence state reset on recovery
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from app.services.anomaly_detector import (
    detect_anomalies,
    reset_persistence_state,
    _consecutive_counts,
)
from app.schemas.metric import MetricIngest
from datetime import datetime, timezone


def make_metric(**overrides) -> MetricIngest:
    """Create a MetricIngest with safe defaults, overriding any fields."""
    defaults = {
        "hostname": "test-host",
        "timestamp": datetime.now(tz=timezone.utc),
        "cpu_usage": 30.0,
        "memory_usage": 40.0,
        "disk_usage": 45.0,
        "load_1m": 0.5,
        "load_5m": 0.4,
        "load_15m": 0.3,
        "cpu_count": 2,
        "memory_available_mb": 4096.0,
        "disk_free_gb": 50.0,
        "network_rx_bytes": 1000,
        "network_tx_bytes": 500,
    }
    defaults.update(overrides)
    return MetricIngest(**defaults)


def setup_function():
    """Clear persistence state before each test."""
    _consecutive_counts.clear()


# ---- Scenario 1: Normal values ----

class TestNormalValues:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_no_anomaly_normal_cpu(self):
        metric = make_metric(cpu_usage=30.0)
        result = detect_anomalies(metric)
        assert result == []

    def test_no_anomaly_all_normal(self):
        """Scenario 1 — Normal: CPU 30%, Memory 40%, Disk 45%, Load low."""
        metric = make_metric(
            cpu_usage=30.0, memory_usage=40.0, disk_usage=45.0, load_1m=0.5
        )
        result = detect_anomalies(metric)
        assert result == []

    def test_boundary_cpu_below_warning(self):
        """CPU at exactly warning - 1 should not trigger."""
        metric = make_metric(cpu_usage=69.9)
        result = detect_anomalies(metric)
        assert not any(a.metric_name == "cpu_usage" for a in result)


# ---- Scenario 2: CPU Spike ----

class TestCPUAnomaly:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_cpu_warning(self):
        """CPU >= 70% → WARNING anomaly."""
        metric = make_metric(cpu_usage=75.0, load_1m=0.5)
        result = detect_anomalies(metric)
        cpu_anomalies = [a for a in result if a.metric_name == "cpu_usage"]
        assert len(cpu_anomalies) == 1
        assert cpu_anomalies[0].severity == "WARNING"

    def test_cpu_critical(self):
        """Scenario 2 — CPU 95%, Memory 40%, Load high → CPU anomaly."""
        metric = make_metric(cpu_usage=95.0, memory_usage=40.0, load_1m=5.0)
        result = detect_anomalies(metric)
        cpu_anomalies = [a for a in result if a.metric_name == "cpu_usage"]
        assert len(cpu_anomalies) == 1
        assert cpu_anomalies[0].severity == "CRITICAL"
        assert cpu_anomalies[0].observed_value == 95.0

    def test_cpu_critical_threshold_exact(self):
        """CPU at exactly 90% should trigger CRITICAL."""
        metric = make_metric(cpu_usage=90.0)
        result = detect_anomalies(metric)
        cpu_anomalies = [a for a in result if a.metric_name == "cpu_usage"]
        assert cpu_anomalies[0].severity == "CRITICAL"


# ---- Scenario 3: Memory Pressure ----

class TestMemoryAnomaly:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_memory_warning(self):
        """Memory >= 75% → WARNING."""
        metric = make_metric(memory_usage=80.0)
        result = detect_anomalies(metric)
        mem = [a for a in result if a.metric_name == "memory_usage"]
        assert len(mem) == 1
        assert mem[0].severity == "WARNING"

    def test_memory_critical(self):
        """Scenario 3 — Memory 95% → CRITICAL."""
        metric = make_metric(cpu_usage=40.0, memory_usage=95.0, load_1m=1.0)
        result = detect_anomalies(metric)
        mem = [a for a in result if a.metric_name == "memory_usage"]
        assert len(mem) == 1
        assert mem[0].severity == "CRITICAL"


# ---- Scenario 5: Disk Pressure ----

class TestDiskAnomaly:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_disk_critical(self):
        """Scenario 5 — Disk 94% → CRITICAL disk anomaly."""
        metric = make_metric(disk_usage=94.0)
        result = detect_anomalies(metric)
        disk = [a for a in result if a.metric_name == "disk_usage"]
        assert len(disk) == 1
        assert disk[0].severity == "CRITICAL"

    def test_disk_warning(self):
        metric = make_metric(disk_usage=82.0)
        result = detect_anomalies(metric)
        disk = [a for a in result if a.metric_name == "disk_usage"]
        assert disk[0].severity == "WARNING"


# ---- Load Threshold Tests ----

class TestLoadAnomaly:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_load_warning(self):
        """Load > cpu_count → WARNING."""
        metric = make_metric(cpu_count=2, load_1m=2.5)
        result = detect_anomalies(metric)
        load = [a for a in result if a.metric_name == "load_1m"]
        assert load[0].severity == "WARNING"

    def test_load_critical(self):
        """Load > 2 × cpu_count → CRITICAL."""
        metric = make_metric(cpu_count=2, load_1m=5.0)
        result = detect_anomalies(metric)
        load = [a for a in result if a.metric_name == "load_1m"]
        assert load[0].severity == "CRITICAL"


# ---- Persistence Tests ----

class TestPersistenceDetection:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_persistence_requires_n_samples(self):
        """
        First 2 samples should not be marked persistent.
        Third sample at cpu >= critical threshold → persistent.
        """
        metric = make_metric(hostname="persist-host", cpu_usage=95.0)

        # Sample 1
        result1 = detect_anomalies(metric)
        cpu1 = [a for a in result1 if a.metric_name == "cpu_usage"]
        assert cpu1[0].is_persistent is False
        assert cpu1[0].consecutive_count == 1

        # Sample 2
        result2 = detect_anomalies(metric)
        cpu2 = [a for a in result2 if a.metric_name == "cpu_usage"]
        assert cpu2[0].is_persistent is False
        assert cpu2[0].consecutive_count == 2

        # Sample 3 — should now be persistent (default consecutive_samples=3)
        result3 = detect_anomalies(metric)
        cpu3 = [a for a in result3 if a.metric_name == "cpu_usage"]
        assert cpu3[0].is_persistent is True
        assert cpu3[0].consecutive_count == 3
        assert cpu3[0].anomaly_type == "persistent_high"

    def test_persistence_resets_on_normal_value(self):
        """Returning to normal resets the consecutive counter."""
        hostname = "reset-host"
        high_metric = make_metric(hostname=hostname, cpu_usage=95.0)
        normal_metric = make_metric(hostname=hostname, cpu_usage=30.0)

        # Trigger 2 high samples
        detect_anomalies(high_metric)
        detect_anomalies(high_metric)

        # Now return to normal
        result = detect_anomalies(normal_metric)
        cpu = [a for a in result if a.metric_name == "cpu_usage"]
        assert cpu == []

        # And verify counter is reset by triggering again
        result2 = detect_anomalies(high_metric)
        cpu2 = [a for a in result2 if a.metric_name == "cpu_usage"]
        assert cpu2[0].consecutive_count == 1
        assert cpu2[0].is_persistent is False


# ---- Scenario 4: Resource Saturation ----

class TestResourceSaturation:
    def setup_method(self):
        _consecutive_counts.clear()

    def test_multiple_anomalies_detected(self):
        """
        Scenario 4 — CPU 95%, Memory 92%, Disk 85%, Load very high → multiple anomalies.

        Note: Disk at 85% is WARNING (critical threshold = 90%) — the detector
        correctly applies independent thresholds per metric.
        CPU, Memory, and Load at these values are all CRITICAL.
        """
        metric = make_metric(
            cpu_usage=95.0,
            memory_usage=92.0,
            disk_usage=85.0,
            load_1m=6.0,
            cpu_count=2,
        )
        result = detect_anomalies(metric)
        metric_names = {a.metric_name for a in result}

        # All 4 metrics are anomalous
        assert "cpu_usage" in metric_names
        assert "memory_usage" in metric_names
        assert "disk_usage" in metric_names
        assert "load_1m" in metric_names

        # CPU, Memory, Load are CRITICAL; disk at 85% is WARNING
        anomaly_by_name = {a.metric_name: a for a in result}
        assert anomaly_by_name["cpu_usage"].severity == "CRITICAL"
        assert anomaly_by_name["memory_usage"].severity == "CRITICAL"
        assert anomaly_by_name["load_1m"].severity == "CRITICAL"
        # Disk 85% < 90% critical threshold → correctly classified as WARNING
        assert anomaly_by_name["disk_usage"].severity == "WARNING"
