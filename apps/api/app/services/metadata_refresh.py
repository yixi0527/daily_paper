from __future__ import annotations

from app.adapters.factory import AdapterFactory
from app.models.article import Article, ArticleAuthor
from app.services.content_policy import ContentPolicyService
from app.services.types import NormalizedArticle, NormalizedAuthor
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload


class MetadataRefreshService:
    def __init__(self) -> None:
        self.factory = AdapterFactory()
        self.content_policy = ContentPolicyService()

    def refresh(self, db: Session, *, missing_only: bool = True) -> dict[str, int]:
        query = (
            select(Article)
            .options(
                joinedload(Article.journal),
                joinedload(Article.authors),
                joinedload(Article.payloads),
            )
            .order_by(Article.published_at.desc(), Article.created_at.desc())
        )
        if missing_only:
            query = query.where(
                or_(Article.abstract.is_(None), Article.abstract == "", Article.snippet.is_(None))
            )

        articles = db.scalars(query).unique().all()
        updated = 0
        skipped = 0

        for article in articles:
            adapter = self.factory.get(article.journal)
            payload = article.payloads[-1].payload_json if article.payloads else None
            source_kind = "crossref" if article.source_name == "crossref" else "rss"

            normalized = None
            if payload:
                normalized = adapter.normalize_article(
                    article.journal,
                    payload,
                    category=article.source_category,
                    source_name=article.source_name,
                    source_kind=source_kind,
                )

            if normalized is None:
                normalized = NormalizedArticle(
                    title=article.title,
                    url=article.url,
                    doi=article.doi,
                    abstract=article.abstract,
                    snippet=article.snippet,
                    source_category=article.source_category,
                    source_name=article.source_name,
                    source_uid=article.source_uid,
                    article_type=article.article_type,
                    volume=article.volume,
                    issue=article.issue,
                    pages=article.pages,
                    article_number=article.article_number,
                    published_at=article.published_at,
                    online_published_at=article.online_published_at,
                    print_published_at=article.print_published_at,
                    accepted_at=article.accepted_at,
                    authors=[
                        NormalizedAuthor(
                            full_name=author.full_name,
                            given_name=author.given_name,
                            family_name=author.family_name,
                            affiliation=author.affiliation,
                        )
                        for author in article.authors
                    ],
                    extra_metadata=article.extra_metadata,
                    raw_payload=payload,
                    payload_format=article.payloads[-1].payload_format if article.payloads else "json",
                )

            normalized = adapter.metadata_enricher.enrich(
                article.journal,
                normalized,
                source_kind=source_kind,
            )

            if not self.content_policy.is_substantive(normalized):
                skipped += 1
                continue

            changed = False
            if normalized.abstract and normalized.abstract != article.abstract:
                article.abstract = normalized.abstract
                changed = True
            if normalized.snippet and normalized.snippet != article.snippet:
                article.snippet = normalized.snippet
                changed = True
            if normalized.article_type and normalized.article_type != article.article_type:
                article.article_type = normalized.article_type
                changed = True
            if normalized.authors and (
                not article.authors
                or ", ".join(author.full_name for author in normalized.authors) != (article.authors_text or "")
            ):
                article.authors = [
                    ArticleAuthor(
                        position=index,
                        given_name=author.given_name,
                        family_name=author.family_name,
                        full_name=author.full_name,
                        affiliation=author.affiliation,
                    )
                    for index, author in enumerate(normalized.authors)
                ]
                article.first_author = normalized.authors[0].full_name
                article.authors_text = ", ".join(author.full_name for author in normalized.authors)
                changed = True
            if changed:
                updated += 1

        db.commit()
        return {"scanned": len(articles), "updated": updated, "skipped": skipped}
