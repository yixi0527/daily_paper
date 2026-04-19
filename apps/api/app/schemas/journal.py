from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel
from pydantic import Field


class JournalOut(ORMModel):
    id: int
    journal_id: str
    slug: str
    journal_name: str
    publisher: str
    issn_print: str | None
    issn_online: str | None
    homepage_url: str
    enabled: bool
    polling_strategy: str
    primary_source: str | None
    fallback_source: str | None


class SourceStateOut(ORMModel):
    source_category: str
    source_name: str
    source_url: str | None
    last_status_code: int | None
    last_checked_at: datetime | None
    last_success_at: datetime | None
    latest_seen_published_at: datetime | None
    last_error: str | None
    consecutive_failures: int


class JournalDetailOut(JournalOut):
    source_states: list[SourceStateOut] = Field(default_factory=list)
