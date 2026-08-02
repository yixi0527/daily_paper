from __future__ import annotations

from datetime import UTC

from app.models.article import Article
from app.schemas.article import ArticleDetailOut, ArticleListItemOut, AuthorOut
from app.schemas.journal import JournalOut, SourceStateOut
from app.services.article_registry import (
    DISPLAY_DATE_CUTOFF,
    ArticleRegistryService,
    display_date,
    get_article_registry,
)


def serialize_journal(journal) -> JournalOut:
    return JournalOut.model_validate(journal)


def serialize_article_list_item(
    article: Article,
    *,
    registry: ArticleRegistryService | None = None,
) -> ArticleListItemOut:
    article_registry = registry or get_article_registry()
    record = article_registry.resolve(
        doi=article.doi,
        journal_slug=article.journal.slug,
        title=article.title,
        abstract=article.abstract,
        snippet=article.snippet,
        first_seen_at=article.first_seen_at,
    )
    resolved_display_date = display_date(
        published_at=article.published_at,
        acquired_at=record.acquired_at,
    )
    comparable_published = (
        article.published_at.replace(tzinfo=UTC)
        if article.published_at is not None and article.published_at.tzinfo is None
        else article.published_at
    )
    display_date_source = (
        "acquired"
        if comparable_published is None or comparable_published > DISPLAY_DATE_CUTOFF
        else "published"
    )
    return ArticleListItemOut(
        id=article.id,
        article_key=record.article_key,
        title=article.title,
        title_zh=record.title_zh,
        doi=article.doi,
        url=article.url,
        abstract=article.abstract,
        abstract_zh=record.abstract_zh,
        snippet=article.snippet,
        translated_at=record.translated_at,
        translation_model=record.translation_model,
        source_category=article.source_category,
        article_type=article.article_type,
        volume=article.volume,
        issue=article.issue,
        published_at=article.published_at,
        acquired_at=record.acquired_at,
        display_date=resolved_display_date,
        display_date_source=display_date_source,
        online_published_at=article.online_published_at,
        print_published_at=article.print_published_at,
        first_author=article.first_author,
        authors_text=article.authors_text,
        authors=[AuthorOut.model_validate(author) for author in article.authors],
        journal=serialize_journal(article.journal),
    )


def serialize_article_detail(
    article: Article,
    *,
    include_raw: bool = False,
    registry: ArticleRegistryService | None = None,
) -> ArticleDetailOut:
    latest_payload = article.payloads[-1].payload_json if include_raw and article.payloads else None
    payload = serialize_article_list_item(article, registry=registry).model_dump()
    payload.update(
        {
            "pages": article.pages,
            "article_number": article.article_number,
            "source_name": article.source_name,
            "source_uid": article.source_uid,
            "extra_metadata": article.extra_metadata,
            "raw_payload": latest_payload,
        }
    )
    return ArticleDetailOut(**payload)


def serialize_source_state(state) -> SourceStateOut:
    return SourceStateOut.model_validate(state)
