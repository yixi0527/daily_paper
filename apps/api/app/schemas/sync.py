from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel
from pydantic import BaseModel, Field


class SyncRunRequest(BaseModel):
    categories: list[str] | None = Field(default=None, description="current_issue / online_first")
    triggered_by: str = "manual"


class SyncRunJournalOut(ORMModel):
    journal_id: int
    source_category: str
    source_name: str | None
    status: str
    attempts: int
    fetched_count: int
    inserted_count: int
    updated_count: int
    failed_count: int
    skipped_count: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None


class SyncRunOut(ORMModel):
    id: str
    triggered_by: str
    scope: str
    requested_journal_slug: str | None
    requested_category: str | None
    status: str
    total_journals: int
    total_processed: int
    total_fetched: int
    total_inserted: int
    total_updated: int
    total_failed: int
    notes: str | None
    started_at: datetime
    finished_at: datetime | None
    journal_runs: list[SyncRunJournalOut] = Field(default_factory=list)
