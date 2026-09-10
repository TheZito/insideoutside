import logging
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_USER_AGENT = "insideoutside/0.1 (personal use; contact via repository)"


class FetchError(Exception):
    """Raised when a source could not be fetched after all retries were exhausted.

    Constitution Principle II: failures MUST be surfaced, never silently dropped.
    """


def fetch_with_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch a URL, retrying transient failures with exponential backoff.

    Raises FetchError (never silently returns None/empty) if every attempt fails.
    """
    own_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    merged_headers = {"User-Agent": DEFAULT_USER_AGENT, **(headers or {})}

    last_error: Exception | None = None
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                response = http_client.get(url, headers=merged_headers)
                response.raise_for_status()
                return response
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                logger.warning(
                    "Fetch attempt %d/%d failed for %s: %s", attempt, max_attempts, url, exc
                )
                if attempt < max_attempts:
                    sleep(backoff_seconds * (2 ** (attempt - 1)))
    finally:
        if own_client:
            http_client.close()

    raise FetchError(f"Failed to fetch {url} after {max_attempts} attempts") from last_error
