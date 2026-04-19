from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes.helpers import serialize_article_list_item
from app.db.session import get_db
from app.schemas.article import SearchHitOut, SearchResponse
from app.schemas.common import PaginationMeta
from app.services.search import SearchService, pagination_meta

router = APIRouter()
service = SearchService()


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=SearchResponse, summary="Search articles")
def search_articles(
    title: str | None = Query(default=None),
    author: str | None = Query(default=None),
    abstract: str | None = Query(default=None),
    journal: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    items, total = service.search(
        db,
        title=title,
        author=author,
        abstract=abstract,
        journal_slugs=_split_csv(journal),
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return SearchResponse(
        items=[
            SearchHitOut(
                article=serialize_article_list_item(item["article"]),
                highlights=item["highlights"],
                score=item["score"],
            )
            for item in items
        ],
        meta=PaginationMeta(**pagination_meta(page, page_size, total)),
    )
