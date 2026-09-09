"""
Security middleware and utilities.

Provides optional API-key authentication for metric ingestion endpoints.
The key is shared between the backend and the monitoring agent and configured
through environment variables — never hard-coded.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_agent_api_key(
    request: Request,
    api_key: str | None = Security(API_KEY_HEADER),
) -> None:
    """
    FastAPI dependency that validates the monitoring-agent API key.

    If MONITORING_AGENT_API_KEY is not configured (empty string), the check
    is skipped and the endpoint is effectively open — suitable for local
    development without the key requirement.

    In production, always set a strong API key.
    """
    settings = get_settings()
    expected_key = settings.monitoring_agent_api_key

    if not expected_key:
        # Key not configured — allow all requests (development mode)
        logger.warning(
            "api_key_check_skipped",
            reason="MONITORING_AGENT_API_KEY not configured",
            path=request.url.path,
        )
        return

    if not api_key or api_key != expected_key:
        logger.warning(
            "api_key_rejected",
            path=request.url.path,
            remote=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
