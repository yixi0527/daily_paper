from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.core.settings import Settings
from app.services.http import (
    TransientHTTPError,
    WaitForTransientHTTP,
    parse_retry_after,
)


class RetryOutcome:
    def __init__(self, exception: BaseException) -> None:
        self._exception = exception

    def exception(self) -> BaseException:
        return self._exception


def retry_state(exception: BaseException, *, attempt_number: int) -> SimpleNamespace:
    return SimpleNamespace(
        attempt_number=attempt_number,
        outcome=RetryOutcome(exception),
    )


def test_rate_limit_wait_uses_long_capped_exponential_backoff() -> None:
    wait = WaitForTransientHTTP(Settings())
    error = TransientHTTPError(429)

    assert wait(retry_state(error, attempt_number=1)) == 10
    assert wait(retry_state(error, attempt_number=2)) == 20
    assert wait(retry_state(error, attempt_number=3)) == 40
    assert wait(retry_state(error, attempt_number=4)) == 60


def test_rate_limit_wait_honors_longer_retry_after() -> None:
    wait = WaitForTransientHTTP(Settings())
    error = TransientHTTPError(429, retry_after_seconds=75)

    assert wait(retry_state(error, attempt_number=1)) == 75


def test_server_error_keeps_short_exponential_backoff() -> None:
    wait = WaitForTransientHTTP(Settings())
    error = TransientHTTPError(503)

    assert wait(retry_state(error, attempt_number=4)) == 8


def test_parse_retry_after_delta_seconds() -> None:
    assert parse_retry_after("45") == 45


def test_parse_retry_after_http_date() -> None:
    now = datetime(2026, 8, 6, 5, 0, tzinfo=UTC)

    assert parse_retry_after("Thu, 06 Aug 2026 05:00:30 GMT", now=now) == 30


def test_parse_retry_after_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        parse_retry_after("later")
