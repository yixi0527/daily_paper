from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SourceSpec:
    name: str
    kind: str
    url: str | None = None
    params: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    source_name: str
    source_kind: str
    source_url: str | None
    items: list[dict[str, Any]]
    payload_format: str
    status_code: int | None
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    request_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedAuthor:
    full_name: str
    given_name: str | None = None
    family_name: str | None = None
    affiliation: str | None = None


@dataclass(slots=True)
class NormalizedArticle:
    title: str
    url: str
    source_category: str
    source_name: str
    source_uid: str | None
    authors: list[NormalizedAuthor]
    doi: str | None = None
    abstract: str | None = None
    snippet: str | None = None
    article_type: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    article_number: str | None = None
    published_at: datetime | None = None
    online_published_at: datetime | None = None
    print_published_at: datetime | None = None
    accepted_at: datetime | None = None
    extra_metadata: dict[str, Any] | None = None
    raw_payload: dict[str, Any] | None = None
    payload_format: str = "json"
