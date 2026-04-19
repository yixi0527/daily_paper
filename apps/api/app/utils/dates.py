from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from time import struct_time

from dateutil import parser


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    if isinstance(value, struct_time):
        return datetime(*value[:6], tzinfo=UTC)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return ensure_utc(parser.parse(stripped))
    return None


def parse_crossref_date_parts(parts: Iterable[Iterable[int]] | None) -> datetime | None:
    if not parts:
        return None
    first = next(iter(parts), None)
    if not first:
        return None
    nums = list(first)
    year = nums[0]
    month = nums[1] if len(nums) > 1 else 1
    day = nums[2] if len(nums) > 2 else 1
    return datetime(year, month, day, tzinfo=UTC)
