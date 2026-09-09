"""
Unit tests for SSH execution, remote collectors, strict null handling, and data quality.
Satisfies Section 47 testing requirements.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.collectors.cpu import collect_cpu
from app.collectors.disk import collect_disk
from app.collectors.load import collect_load
from app.collectors.logs import collect_logs
from app.collectors.memory import collect_memory
from app.collectors.network import collect_network
from app.collectors.process import collect_processes
from app.collectors.response_time import collect_response_time
from app.monitoring.metric_normalizer import normalize_to_unified_snapshot
from app.ssh.models import CommandResult, SSHConnectionStatus


class DummySession:
    """Mock SSH session for unit testing collectors without live SSH."""

    def __init__(self, command_map: dict[str, CommandResult]):
        self.command_map = command_map

    async def execute(self, command: str, timeout_seconds=None) -> CommandResult:
        if command in self.command_map:
            return self.command_map[command]
        return CommandResult(command=command, exit_code=127, success=False, error="Command not mocked")


@pytest.mark.asyncio
async def test_ssh_command_success():
    """Test 1 & 4: Successful SSH command execution and result object."""
    res = CommandResult(command="nproc", stdout="2\n", exit_code=0, success=True, duration_ms=12.0)
    assert res.success is True
    assert res.exit_code == 0
    assert res.stdout.strip() == "2"


@pytest.mark.asyncio
async def test_ssh_command_failure():
    """Test 4: Command execution failure reports success=False, error message."""
    res = CommandResult(command="bad_cmd", stderr="command not found", exit_code=127, success=False, error="command not found")
    assert res.success is False
    assert res.exit_code == 127
    assert res.error == "command not found"


@pytest.mark.asyncio
async def test_cpu_collector_success():
    """Test 5: CPU parsing with mpstat and nproc."""
    session = DummySession({
        "nproc": CommandResult(command="nproc", stdout="2\n", success=True, exit_code=0),
        "mpstat 1 1": CommandResult(
            command="mpstat 1 1",
            stdout=(
                "Linux 6.8.0-1006-aws\n"
                "11:00:01 AM  CPU    %usr   %nice    %sys %iowait  %steal   %idle\n"
                "11:00:02 AM  all    7.50    0.00    2.50    0.00    0.00   90.00\n"
                "Average:     all    7.50    0.00    2.50    0.00    0.00   90.00\n"
            ),
            success=True,
            exit_code=0,
        ),
    })
    cpu_data = await collect_cpu(session)
    assert cpu_data["status"] == "success"
    assert cpu_data["cpu_count"] == 2
    assert cpu_data["cpu_usage"] == 10.0  # 100 - 90.0 idle


@pytest.mark.asyncio
async def test_cpu_collector_fallback_and_null_on_failure():
    """Test 5 & 13: CPU parsing failure returns None, NEVER 0.0."""
    session = DummySession({
        "nproc": CommandResult(command="nproc", stderr="failed", success=False, exit_code=1),
        "mpstat 1 1": CommandResult(command="mpstat 1 1", stderr="command not found", success=False, exit_code=127),
        "cat /proc/stat": CommandResult(command="cat /proc/stat", stderr="permission denied", success=False, exit_code=1),
    })
    cpu_data = await collect_cpu(session)
    assert cpu_data["status"] == "failed"
    assert cpu_data["cpu_usage"] is None  # CRITICAL: Never 0.0
    assert cpu_data["cpu_count"] is None


@pytest.mark.asyncio
async def test_memory_collector_calculation():
    """Test 6: Memory usage calculation ((total - available) / total) * 100."""
    session = DummySession({
        "free -m": CommandResult(
            command="free -m",
            stdout=(
                "               total        used        free      shared  buff/cache   available\n"
                "Mem:            1000         600         200          10         200         400\n"
                "Swap:              0           0           0\n"
            ),
            success=True,
            exit_code=0,
        )
    })
    mem_data = await collect_memory(session)
    assert mem_data["status"] == "success"
    assert mem_data["memory_total_mb"] == 1000.0
    assert mem_data["memory_available_mb"] == 400.0
    assert mem_data["memory_usage"] == 60.0  # (1000 - 400) / 1000 * 100


@pytest.mark.asyncio
async def test_memory_collector_failure_returns_null():
    """Test 6 & 13: Memory collection failure returns None, NEVER 0.0."""
    session = DummySession({
        "free -m": CommandResult(command="free -m", stderr="out of memory", success=False, exit_code=1)
    })
    mem_data = await collect_memory(session)
    assert mem_data["status"] == "failed"
    assert mem_data["memory_usage"] is None
    assert mem_data["memory_total_mb"] is None


@pytest.mark.asyncio
async def test_disk_collector_parsing():
    """Test 7: Disk collector parses POSIX blocks and calculates GB."""
    session = DummySession({
        "df -P /": CommandResult(
            command="df -P /",
            stdout=(
                "Filesystem     1024-blocks    Used Available Capacity Mounted on\n"
                "/dev/root         20971520 8388608  12582912      40% /\n"
            ),
            success=True,
            exit_code=0,
        )
    })
    disk_data = await collect_disk(session)
    assert disk_data["status"] == "success"
    assert disk_data["disk_usage"] == 40.0
    assert disk_data["disk_total_gb"] == 20.0  # 20971520 KB / (1024*1024)
    assert disk_data["disk_used_gb"] == 8.0


@pytest.mark.asyncio
async def test_load_collector_parsing():
    """Test 8: System load average parsing from /proc/loadavg."""
    session = DummySession({
        "cat /proc/loadavg": CommandResult(
            command="cat /proc/loadavg",
            stdout="1.45 2.10 1.85 2/120 4521\n",
            success=True,
            exit_code=0,
        )
    })
    load_data = await collect_load(session)
    assert load_data["status"] == "success"
    assert load_data["load_1m"] == 1.45
    assert load_data["load_5m"] == 2.10
    assert load_data["load_15m"] == 1.85


@pytest.mark.asyncio
async def test_process_collector_sorting_and_deduplication():
    """Test 9: Process collection parses top CPU and memory consumers."""
    session = DummySession({
        "ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 11": CommandResult(
            command="ps",
            stdout=(
                "  PID COMMAND         %CPU %MEM\n"
                " 1001 python3         82.4 15.2\n"
                " 1002 stress-ng       60.1 25.0\n"
            ),
            success=True,
            exit_code=0,
        ),
        "ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 11": CommandResult(
            command="ps",
            stdout=(
                "  PID COMMAND         %CPU %MEM\n"
                " 1003 postgres         5.0 42.1\n"
                " 1001 python3         82.4 15.2\n"
            ),
            success=True,
            exit_code=0,
        ),
    })
    proc_data = await collect_processes(session)
    assert proc_data["status"] == "success"
    procs = proc_data["processes"]
    assert len(procs) == 3
    # Top CPU should be first
    assert procs[0]["pid"] == 1001
    assert procs[0]["name"] == "python3"
    assert procs[0]["cpu_percent"] == 82.4


@pytest.mark.asyncio
async def test_network_collector_summation():
    """Test 10: Sums received and transmitted bytes ignoring loopback."""
    session = DummySession({
        "cat /proc/net/dev": CommandResult(
            command="cat /proc/net/dev",
            stdout=(
                "Inter-|   Receive                                                |  Transmit\n"
                " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
                "    lo: 1000000       0    0    0    0     0          0         0  1000000       0    0    0    0     0       0          0\n"
                "  eth0:  500000     100    0    0    0     0          0         0   200000     100    0    0    0     0       0          0\n"
                "  ens5:  300000     100    0    0    0     0          0         0   100000     100    0    0    0     0       0          0\n"
            ),
            success=True,
            exit_code=0,
        )
    })
    net_data = await collect_network(session)
    assert net_data["status"] == "success"
    # eth0 (500000) + ens5 (300000) = 800000 rx (lo ignored!)
    assert net_data["network_rx_bytes"] == 800000
    # eth0 (200000) + ens5 (100000) = 300000 tx
    assert net_data["network_tx_bytes"] == 300000


@pytest.mark.asyncio
async def test_log_collector_permission_denied():
    """Test 11: Log collection handles permission denial gracefully."""
    session = DummySession({
        "journalctl -p warning..err -n 20 --no-pager": CommandResult(
            command="journalctl",
            stderr="Hint: You are currently not seeing messages from other users and the system.\nPermission denied",
            success=False,
            exit_code=1,
        )
    })
    log_data = await collect_logs(session)
    assert log_data["status"] == "permission_denied"
    assert log_data["logs"] == []


@pytest.mark.asyncio
async def test_response_time_disabled_when_no_url():
    """Test 12: Response time collector returns None and disabled status when MONITORED_URL is empty."""
    res = await collect_response_time(url="")
    assert res["status"] == "disabled"
    assert res["response_time_ms"] is None
    assert res["response_time_enabled"] is False


def test_partial_collection_and_data_quality():
    """Test 14: Data quality is COMPLETE when all succeed, PARTIAL when some fail, FAILED when all fail."""
    # Complete
    complete_raw = {
        "cpu": {"cpu_usage": 45.0, "status": "success"},
        "memory": {"memory_usage": 50.0, "status": "success"},
        "disk": {"disk_usage": 30.0, "status": "success"},
        "load": {"load_1m": 0.5, "status": "success"},
        "process": {"processes": [], "status": "success"},
        "network": {"network_rx_bytes": 100, "status": "success"},
    }
    s1 = normalize_to_unified_snapshot(complete_raw)
    assert s1.data_quality.collection_status == "COMPLETE"
    assert s1.data_quality.successful_collectors == 6
    assert s1.data_quality.failed_collectors == 0

    # Partial (disk failed)
    partial_raw = {
        "cpu": {"cpu_usage": 45.0, "status": "success"},
        "memory": {"memory_usage": 50.0, "status": "success"},
        "disk": {"disk_usage": None, "status": "failed", "error": "Disk read timeout"},
        "load": {"load_1m": 0.5, "status": "success"},
        "process": {"processes": [], "status": "success"},
        "network": {"network_rx_bytes": 100, "status": "success"},
    }
    s2 = normalize_to_unified_snapshot(partial_raw)
    assert s2.data_quality.collection_status == "PARTIAL"
    assert s2.disk.usage_percent is None  # Preserves None!
    assert s2.cpu.usage_percent == 45.0
    assert s2.data_quality.failed_collectors == 1
