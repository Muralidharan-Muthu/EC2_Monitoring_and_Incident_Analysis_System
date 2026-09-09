"""
Collector service orchestrating all remote collectors over SSH.
Safely handles connection errors, partial collection, and timeouts.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from app.collectors.cpu import collect_cpu
from app.collectors.disk import collect_disk
from app.collectors.load import collect_load
from app.collectors.logs import collect_logs
from app.collectors.memory import collect_memory
from app.collectors.network import collect_network
from app.collectors.process import collect_processes
from app.collectors.response_time import collect_response_time
from app.collectors.system import collect_system_info
from app.core.logging import get_logger

logger = get_logger(__name__)
from app.monitoring.metric_normalizer import normalize_to_unified_snapshot
from app.schemas.monitoring import UnifiedSnapshot
from app.ssh.client import EC2SSHClient, get_ssh_client


class CollectorService:
    """Orchestrates all metric collectors for the EC2 remote host."""

    def __init__(self, ssh_client: EC2SSHClient | None = None):
        self._ssh_client = ssh_client or get_ssh_client()

    async def collect_snapshot(self) -> UnifiedSnapshot:
        """
        Execute a complete collection cycle over SSH.
        Returns a UnifiedSnapshot with exact measured values or None for failures.
        """
        raw_results: Dict[str, Any] = {}
        errors: list[str] = []

        try:
            async with self._ssh_client.session() as session:
                # Run independent collectors within the active SSH session
                # CPU, Memory, Disk, Load, System, Net, Logs, Procs
                cpu_task = collect_cpu(session)
                mem_task = collect_memory(session)
                disk_task = collect_disk(session)
                load_task = collect_load(session)
                sys_task = collect_system_info(session)
                net_task = collect_network(session)
                logs_task = collect_logs(session)
                proc_task = collect_processes(session)
                resp_task = collect_response_time()

                (
                    raw_results["cpu"],
                    raw_results["memory"],
                    raw_results["disk"],
                    raw_results["load"],
                    raw_results["system"],
                    raw_results["network"],
                    raw_results["logs"],
                    raw_results["process"],
                    raw_results["response_time"],
                ) = await asyncio.gather(
                    cpu_task,
                    mem_task,
                    disk_task,
                    load_task,
                    sys_task,
                    net_task,
                    logs_task,
                    proc_task,
                    resp_task,
                    return_exceptions=False,
                )

        except Exception as exc:
            err_msg = f"SSH connection or execution failed: {exc}"
            logger.error(err_msg)
            errors.append(err_msg)
            # Fill missing collectors with failure state
            for col in ["cpu", "memory", "disk", "load", "system", "network", "logs", "process"]:
                if col not in raw_results:
                    raw_results[col] = {"status": "failed", "error": err_msg}
            if "response_time" not in raw_results:
                raw_results["response_time"] = await collect_response_time()

        snapshot = normalize_to_unified_snapshot(raw_results, errors)
        return snapshot


_collector_service: CollectorService | None = None


def get_collector_service() -> CollectorService:
    global _collector_service
    if _collector_service is None:
        _collector_service = CollectorService()
    return _collector_service
