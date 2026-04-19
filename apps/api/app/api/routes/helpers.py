from __future__ import annotations

from app.models.article import Article
from app.schemas.article import ArticleDetailOut, ArticleListItemOut, AuthorOut
from app.schemas.journal import JournalOut, SourceStateOut


def serialize_journal(journal) -> JournalOut:
    return JournalOut.model_validate(journal)


def serialize_article_list_item(article: Article) -> ArticleListItemOut:
    return ArticleListItemOut(
        id=article.id,
        title=article.title,
        doi=article.doi,
        url=article.url,
        snippet=article.snippet,
        source_category=article.source_category,
        article_type=article.article_type,
        volume=article.volume,
        issue=article.issue,
        published_at=article.published_at,
        online_published_at=article.online_published_at,
        print_published_at=article.print_published_at,
        first_author=article.first_author,
        authors_text=article.authors_text,
        journal=serialize_journal(article.journal),
    )


def serialize_article_detail(article: Article, *, include_raw: bool = False) -> ArticleDetailOut:
    latest_payload = article.payloads[-1].payload_json if include_raw and article.payloads else None
    return ArticleDetailOut(
        **serialize_article_list_item(article).model_dump(),
        abstract=article.abstract,
        pages=article.pages,
        article_number=article.article_number,
        source_name=article.source_name,
        source_uid=article.source_uid,
        extra_metadata=article.extra_metadata,
        authors=[AuthorOut.model_validate(author) for author in article.authors],
        raw_payload=latest_payload,
    )


def serialize_source_state(state) -> SourceStateOut:
    return SourceStateOut.model_validate(state)
