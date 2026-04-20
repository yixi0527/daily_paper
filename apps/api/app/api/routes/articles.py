from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.routes.helpers import serialize_article_detail, serialize_article_list_item
from app.core.settings import get_settings
from app.db.session import get_db
from app.models.article import Article
from app.schemas.article import ArticleDetailOut, ArticleListResponse
from app.schemas.common import PaginationMeta
from app.services.search import SearchService, pagination_meta

router = APIRouter()
service = SearchService()


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=ArticleListResponse, summary="List tracked articles")
def list_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    journal: str | None = Query(default=None, description="Comma-separated journal slugs"),
    author: str | None = Query(default=None, description="Case-insensitive author name filter"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    source_category: str | None = Query(default=None),
    article_type: str | None = Query(default=None),
    has_doi: bool | None = Query(default=None),
    has_abstract: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ArticleListResponse:
    items, total = service.list_articles(
        db,
        page=page,
        page_size=page_size,
        journal_slugs=_split_csv(journal),
        author_contains=author,
        date_from=date_from,
        date_to=date_to,
        source_category=source_category,
        article_type=article_type,
        has_doi=has_doi,
        has_abstract=has_abstract,
    )
    return ArticleListResponse(
        items=[serialize_article_list_item(item) for item in items],
        meta=PaginationMeta(**pagination_meta(page, page_size, total)),
    )


@router.get("/{article_id}", response_model=ArticleDetailOut, summary="Get article detail")
def get_article(article_id: str, db: Session = Depends(get_db)) -> ArticleDetailOut:
    article = db.scalar(
        select(Article)
        .options(
            joinedload(Article.journal), joinedload(Article.authors), joinedload(Article.payloads)
        )
        .where(Article.id == article_id)
    )
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return serialize_article_detail(article, include_raw=get_settings().app_debug)
