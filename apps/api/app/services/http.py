from __future__ import annotations

import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from threading import Lock
from urllib.parse import urlparse

import httpx
from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt

logger = get_logger(__name__)


class TransientHTTPError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"transient http status {status_code}")


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized.isdecimal():
        return float(normalized)
    retry_at = parsedate_to_datetime(normalized)
    if retry_at is None or retry_at.tzinfo is None:
        raise ValueError(f"Invalid Retry-After header: {value!r}")
    reference_time = now
    if reference_time is None:
        reference_time = datetime.now(tz=UTC)
    if reference_time.tzinfo is None:
        raise ValueError("Retry-After reference time must be timezone-aware")
    return max(0.0, (retry_at - reference_time).total_seconds())


class WaitForTransientHTTP:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def __call__(self, retry_state: RetryCallState) -> float:
        outcome = retry_state.outcome
        if outcome is None:
            raise RuntimeError("Retry wait evaluated without an outcome")
        exception = outcome.exception()
        if exception is None:
            raise RuntimeError("Retry wait evaluated without an exception")
        exponent = retry_state.attempt_number - 1
        standard_wait = min(
            2**exponent,
            self.settings.sync_retry_max_backoff_seconds,
        )
        if not isinstance(exception, TransientHTTPError) or exception.status_code != 429:
            return standard_wait
        rate_limit_wait = min(
            self.settings.sync_rate_limit_backoff_seconds * (2**exponent),
            self.settings.sync_rate_limit_max_backoff_seconds,
        )
        if exception.retry_after_seconds is not None:
            return max(rate_limit_wait, exception.retry_after_seconds)
        return rate_limit_wait


class HTTPClientService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=self.settings.sync_http_timeout,
            headers={"User-Agent": self.settings.http_user_agent},
        )
        self._host_last_request: dict[str, float] = {}
        self._lock = Lock()

    def close(self) -> None:
        self.client.close()

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        min_interval = self.settings.sync_min_interval_seconds
        with self._lock:
            previous = self._host_last_request.get(host)
            now = time.monotonic()
            if previous:
                elapsed = now - previous
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
            self._host_last_request[host] = time.monotonic()

    @retry(
        reraise=True,
        stop=stop_after_attempt(get_settings().sync_retry_attempts),
        wait=WaitForTransientHTTP(get_settings()),
        retry=retry_if_exception_type((httpx.RequestError, TransientHTTPError)),
    )
    def get(
        self, url: str, *, params: dict | None = None, headers: dict | None = None
    ) -> httpx.Response:
        self._throttle(url)
        response = self.client.get(url, params=params, headers=headers)
        if response.status_code in {429, 500, 502, 503, 504}:
            logger.warning("Transient HTTP status for %s: %s", url, response.status_code)
            retry_after_seconds = parse_retry_after(response.headers.get("Retry-After"))
            raise TransientHTTPError(
                response.status_code,
                retry_after_seconds=retry_after_seconds,
            )
        return response
