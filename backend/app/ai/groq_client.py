"""
Groq API client with retry logic and graceful error handling.

The LLM is an optional enhancement. If Groq is unavailable, the system
continues operating with rule-based analysis.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from groq import Groq, APIError, APIConnectionError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_groq_client() -> Optional[Groq]:
    """Return a Groq client if the API key is configured, else None."""
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("groq_client_unavailable", reason="GROQ_API_KEY not configured")
        return None
    return Groq(api_key=settings.groq_api_key)


@retry(
    retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_groq(client: Groq, model: str, messages: list[dict]) -> str:
    """Make a Groq API call with retry on transient errors."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,  # Low temperature for consistent, factual output
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def call_groq_for_analysis(
    prompt_messages: list[dict[str, str]],
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Call the Groq LLM for incident analysis.

    Returns:
        (parsed_json, error_message)
        - On success: (dict, None)
        - On failure: (None, error_message)

    This function NEVER raises — all errors are returned as strings
    so callers can implement graceful fallback.
    """
    settings = get_settings()
    client = _get_groq_client()

    if client is None:
        return None, "Groq API key not configured"

    model = settings.groq_model

    try:
        raw_response = _call_groq(client, model, prompt_messages)
        logger.debug("groq_raw_response", length=len(raw_response))

        parsed = json.loads(raw_response)
        logger.info("groq_analysis_success", model=model)
        return parsed, None

    except json.JSONDecodeError as exc:
        error = f"Groq returned invalid JSON: {exc}"
        logger.warning("groq_json_parse_error", error=error)
        return None, error

    except RateLimitError as exc:
        error = f"Groq rate limit exceeded: {exc}"
        logger.warning("groq_rate_limit", error=error)
        return None, error

    except APIConnectionError as exc:
        error = f"Groq connection error: {exc}"
        logger.warning("groq_connection_error", error=error)
        return None, error

    except APIError as exc:
        error = f"Groq API error: {exc}"
        logger.warning("groq_api_error", error=error)
        return None, error

    except Exception as exc:
        error = f"Unexpected error calling Groq: {exc}"
        logger.error("groq_unexpected_error", error=error)
        return None, error
