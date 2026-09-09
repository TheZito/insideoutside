import httpx
import pytest

from openinsider_tracker.ingestion.http_client import FetchError, fetch_with_retry


def test_transient_failure_is_retried_then_succeeds():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    sleeps = []

    response = fetch_with_retry(
        "https://example.test/data",
        client=client,
        max_attempts=3,
        backoff_seconds=0.01,
        sleep=sleeps.append,
    )

    assert response.status_code == 200
    assert len(attempts) == 3
    assert len(sleeps) == 2


def test_persistent_failure_raises_fetch_error_not_silently_dropped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    with pytest.raises(FetchError):
        fetch_with_retry(
            "https://example.test/data",
            client=client,
            max_attempts=3,
            backoff_seconds=0.01,
            sleep=lambda _seconds: None,
        )
