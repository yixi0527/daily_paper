from __future__ import annotations

from app.schemas.article import ArticleListItemOut
from app.schemas.common import TimeSeriesPoint
from pydantic import BaseModel


class JournalCount(BaseModel):
    journal_slug: str
    journal_name: str
    count: int


class DashboardOut(BaseModel):
    today_new_articles: int
    last_sync_status: str | None
    trend: list[TimeSeriesPoint]
    by_journal: list[JournalCount]
    latest_articles: list[ArticleListItemOut]
