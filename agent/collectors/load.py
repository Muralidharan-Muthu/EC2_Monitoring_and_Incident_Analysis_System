"""
Optional HTTP response time collector.

Measures the response time of a configured URL (e.g., the application
running on the EC2 instance). If no URL is configured, this collector
gracefully disables itself.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


def collect_response_time(url: Optional[str], timeout: int = 10) -> dict:
    """
    Measure HTTP response time for the given URL.

    Args:
        url: Target URL. If None or empty, returns None values.
        timeout: Request timeout in seconds.

    Returns:
        dict with response_time_ms, http_status.
        Both values are None if url is not configured.
    """
    result = {
        "response_time_ms": None,
        "http_status": None,
    }

    if not url:
        return result

    start = time.monotonic()
    try:
        with urlopen(url, timeout=timeout) as response:
            elapsed = (time.monotonic() - start) * 1000
            result["response_time_ms"] = round(elapsed, 2)
            result["http_status"] = response.status
    except HTTPError as exc:
        elapsed = (time.monotonic() - start) * 1000
        result["response_time_ms"] = round(elapsed, 2)
        result["http_status"] = exc.code
    except URLError as exc:
        logger.warning("response_time_url_error %s: %s", url, exc)
    except Exception as exc:
        logger.warning("response_time_error: %s", exc)

    return result
