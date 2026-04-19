from __future__ import annotations

import time
from threading import Lock
from urllib.parse import urlparse

import httpx
from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = get_logger(__name__)


class TransientHTTPError(RuntimeError):
    pass


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
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, TransientHTTPError)),
    )
    def get(
        self, url: str, *, params: dict | None = None, headers: dict | None = None
    ) -> httpx.Response:
        self._throttle(url)
        response = self.client.get(url, params=params, headers=headers)
        if response.status_code in {429, 500, 502, 503, 504}:
            logger.warning("Transient HTTP status for %s: %s", url, response.status_code)
            raise TransientHTTPError(f"transient http status {response.status_code}")
        return response
