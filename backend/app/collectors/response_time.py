"""Optional HTTP application response-time collector."""

from __future__ import annotations

import time
from typing import Any, Optional
import httpx
from app.core.config import get_settings


async def collect_response_time(url: Optional[str] = None) -> dict[str, Any]:
    """
    Measure HTTP response time and status code for MONITORED_URL from the backend.

    If MONITORED_URL is not configured, returns None for metrics and status="disabled".
    Never fabricates a response time.
    """
    settings = get_settings()
    target_url = url or settings.monitored_url

    if not target_url or not target_url.strip():
        return {
            "response_time_ms": None,
            "http_status": None,
            "response_time_enabled": False,
            "url": None,
            "status": "disabled",
            "error": None,
        }

    target_url = target_url.strip()
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(target_url)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "response_time_ms": elapsed_ms,
                "http_status": resp.status_code,
                "response_time_enabled": True,
                "url": target_url,
                "status": "success",
                "error": None,
            }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "response_time_ms": elapsed_ms,
            "http_status": None,
            "response_time_enabled": True,
            "url": target_url,
            "status": "failed",
            "error": f"HTTP probe failed: {exc}",
        }
