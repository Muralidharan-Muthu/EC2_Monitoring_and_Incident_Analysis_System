"""
HTTP sender — delivers metric payloads to the FastAPI backend.

Implements retry logic with exponential backoff for transient network failures.
Never crashes the agent; always logs failures safely.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import AgentConfig

logger = logging.getLogger(__name__)


def _build_headers(config: AgentConfig) -> dict[str, str]:
    """Build request headers including optional API key."""
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["X-API-Key"] = config.api_key
    return headers


def send_metrics(payload: dict[str, Any], config: AgentConfig) -> bool:
    """
    Send a metrics payload to the FastAPI backend.

    Returns True on success, False on failure.
    Never raises — all errors are logged and returned as False.
    """
    headers = _build_headers(config)

    for attempt in range(1, config.max_retries + 1):
        try:
            with httpx.Client(timeout=config.request_timeout) as client:
                response = client.post(
                    config.metrics_endpoint,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                logger.info(
                    "metrics_sent successfully status=%s", response.status_code
                )
                return True

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "metrics_send_http_error attempt=%d/%d status=%d",
                attempt, config.max_retries, exc.response.status_code,
            )
        except httpx.ConnectError as exc:
            logger.warning(
                "metrics_send_connect_error attempt=%d/%d: %s",
                attempt, config.max_retries, exc,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "metrics_send_timeout attempt=%d/%d: %s",
                attempt, config.max_retries, exc,
            )
        except Exception as exc:
            logger.error("metrics_send_unexpected_error: %s", exc)
            return False

        if attempt < config.max_retries:
            wait = config.retry_wait * attempt
            logger.info("retrying in %ds...", wait)
            time.sleep(wait)

    logger.error(
        "metrics_send_failed after %d attempts", config.max_retries
    )
    return False
