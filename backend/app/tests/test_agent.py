"""
Agent unit tests — metric collection and safe error handling.
"""

from __future__ import annotations

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "agent"))


class TestSafeCollect:
    """Tests for the _safe_collect wrapper in monitor_agent.py."""

    def test_safe_collect_returns_result(self):
        from monitor_agent import _safe_collect
        result = _safe_collect("test", lambda: {"key": "value"})
        assert result == {"key": "value"}

    def test_safe_collect_returns_empty_on_exception(self):
        from monitor_agent import _safe_collect
        def failing_collector():
            raise RuntimeError("Collection failed")
        result = _safe_collect("test", failing_collector)
        assert result == {}

    def test_safe_collect_handles_none_return(self):
        from monitor_agent import _safe_collect
        result = _safe_collect("test", lambda: None)
        assert result == {}


class TestDiskCollector:
    def test_collect_disk_valid_path(self):
        from collectors.disk import collect_disk
        result = collect_disk(".")
        assert "disk_usage" in result
        assert "disk_free_gb" in result
        assert 0 <= result["disk_usage"] <= 100

    def test_collect_disk_invalid_path(self):
        from collectors.disk import collect_disk
        result = collect_disk("/nonexistent/path/xyz")
        assert result["disk_usage"] == 0.0


class TestSystemInfoCollector:
    def test_hostname_collected(self):
        from collectors.system import collect_system_info
        result = collect_system_info()
        assert "hostname" in result
        assert result["hostname"] != ""

    def test_os_name_collected(self):
        from collectors.system import collect_system_info
        result = collect_system_info()
        assert "os_name" in result


class TestNetworkCollector:
    def test_network_returns_bytes(self):
        from collectors.network import collect_network
        result = collect_network()
        assert "network_rx_bytes" in result
        assert "network_tx_bytes" in result
        assert result["network_rx_bytes"] >= 0


class TestResponseTimeCollector:
    def test_no_url_returns_none(self):
        from collectors.load import collect_response_time
        result = collect_response_time(None)
        assert result["response_time_ms"] is None
        assert result["http_status"] is None

    def test_empty_url_returns_none(self):
        from collectors.load import collect_response_time
        result = collect_response_time("")
        assert result["response_time_ms"] is None

    def test_invalid_url_returns_none(self):
        from collectors.load import collect_response_time
        # Should not raise
        result = collect_response_time("http://invalid.host.that.does.not.exist.xyz")
        assert result["response_time_ms"] is None
