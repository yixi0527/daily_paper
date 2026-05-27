from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel, PaginationMeta
from app.schemas.journal import JournalOut
from pydantic import BaseModel, Field


class AuthorOut(ORMModel):
    position: int
    given_name: str | None
    family_name: str | None
    full_name: str
    affiliation: str | None


class ArticleListItemOut(ORMModel):
    id: str
    title: str
    title_zh: str | None
    doi: str | None
    url: str
    abstract: str | None
    abstract_zh: str | None
    snippet: str | None
    analysis_generated_at: datetime | None
    source_category: str
    article_type: str | None
    volume: str | None
    issue: str | None
    published_at: datetime | None
    online_published_at: datetime | None
    print_published_at: datetime | None
    first_author: str | None
    authors_text: str | None
    authors: list[AuthorOut] = Field(default_factory=list)
    journal: JournalOut


class ArticleDetailOut(ArticleListItemOut):
    pages: str | None
    article_number: str | None
    source_name: str
    source_uid: str | None
    related_literature: list[dict] | None
    related_literature_notes_zh: list[str] | None
    heuristic_thoughts_zh: list[str] | None
    analysis_model: str | None
    extra_metadata: dict | None
    raw_payload: dict | None = None


class ArticleAnalysisRequest(BaseModel):
    force: bool = False


class ArticleAnalysisRunRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=200)
    force: bool = False


class ArticleAnalysisRunOut(BaseModel):
    scanned: int
    updated: int


class ArticleListResponse(BaseModel):
    items: list[ArticleListItemOut]
    meta: PaginationMeta


class SearchHitOut(BaseModel):
    article: ArticleListItemOut
    highlights: dict[str, str]
    score: float


class SearchResponse(BaseModel):
    items: list[SearchHitOut]
    meta: PaginationMeta
