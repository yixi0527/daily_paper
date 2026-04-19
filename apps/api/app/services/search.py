from __future__ import annotations

import math
import re
from datetime import UTC, datetime

from app.models.article import Article
from app.models.journal import Journal
from rapidfuzz import fuzz
from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session, joinedload


class SearchService:
    def build_article_query(
        self,
        *,
        journal_slugs: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source_category: str | None = None,
        article_type: str | None = None,
        has_doi: bool | None = None,
        has_abstract: bool | None = None,
    ) -> Select[tuple[Article]]:
        query = select(Article).options(joinedload(Article.journal), joinedload(Article.authors))
        if journal_slugs:
            query = query.join(Article.journal).where(Journal.slug.in_(journal_slugs))
        if date_from:
            query = query.where(Article.published_at >= date_from.astimezone(UTC))
        if date_to:
            query = query.where(Article.published_at <= date_to.astimezone(UTC))
        if source_category:
            query = query.where(Article.source_category == source_category)
        if article_type:
            query = query.where(Article.article_type == article_type)
        if has_doi is True:
            query = query.where(Article.doi.is_not(None))
        if has_doi is False:
            query = query.where(Article.doi.is_(None))
        if has_abstract is True:
            query = query.where(Article.abstract.is_not(None))
        if has_abstract is False:
            query = query.where(Article.abstract.is_(None))
        return query

    def list_articles(
        self,
        db: Session,
        *,
        page: int,
        page_size: int,
        journal_slugs: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source_category: str | None = None,
        article_type: str | None = None,
        has_doi: bool | None = None,
        has_abstract: bool | None = None,
    ) -> tuple[list[Article], int]:
        query = self.build_article_query(
            journal_slugs=journal_slugs,
            date_from=date_from,
            date_to=date_to,
            source_category=source_category,
            article_type=article_type,
            has_doi=has_doi,
            has_abstract=has_abstract,
        ).order_by(desc(Article.published_at), desc(Article.created_at))
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (page - 1) * page_size
        items = db.scalars(query.offset(offset).limit(page_size)).unique().all()
        return items, total

    def search(
        self,
        db: Session,
        *,
        title: str | None,
        author: str | None,
        abstract: str | None,
        journal_slugs: list[str] | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        base_query = self.build_article_query(
            journal_slugs=journal_slugs,
            date_from=date_from,
            date_to=date_to,
        ).order_by(desc(Article.published_at), desc(Article.created_at))
        candidate_articles = db.scalars(base_query.limit(500)).unique().all()
        hits = []
        for article_obj in candidate_articles:
            match = self._score_article(article_obj, title=title, author=author, abstract=abstract)
            if match:
                hits.append(match)
        hits.sort(
            key=lambda item: (
                item["score"],
                item["article"].published_at or datetime.min.replace(tzinfo=UTC),
            ),
            reverse=True,
        )
        total = len(hits)
        start = (page - 1) * page_size
        end = start + page_size
        return hits[start:end], total

    def _score_article(
        self, article: Article, *, title: str | None, author: str | None, abstract: str | None
    ) -> dict | None:
        title_score = (
            100.0 if not title else fuzz.partial_ratio(title.lower(), article.title.lower())
        )
        author_score = 100.0
        if author:
            author_candidates = [item.full_name for item in article.authors] or [
                article.authors_text or ""
            ]
            author_score = max(
                (fuzz.WRatio(author.lower(), candidate.lower()) for candidate in author_candidates),
                default=0.0,
            )
        abstract_score = 100.0
        if abstract:
            abstract_text = (article.abstract or article.snippet or "").lower()
            abstract_score = (
                fuzz.partial_ratio(abstract.lower(), abstract_text) if abstract_text else 0.0
            )
        if title and title_score < 55:
            return None
        if author and author_score < 60:
            return None
        if abstract and abstract_score < 50:
            return None
        score = round((title_score * 0.45) + (author_score * 0.35) + (abstract_score * 0.20), 2)
        highlights = {}
        if title:
            highlights["title"] = self._highlight(article.title, title)
        if author:
            highlights["author"] = self._highlight(article.authors_text or "", author)
        if abstract:
            highlights["abstract"] = self._highlight(
                article.abstract or article.snippet or "", abstract
            )
        return {"article": article, "score": score, "highlights": highlights}

    def _highlight(self, haystack: str, needle: str) -> str:
        if not haystack or not needle:
            return haystack
        pattern = re.compile(re.escape(needle), re.IGNORECASE)
        if pattern.search(haystack):
            return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", haystack, count=2)
        return haystack


def pagination_meta(page: int, page_size: int, total: int) -> dict[str, int]:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)) if page_size else 1,
    }
