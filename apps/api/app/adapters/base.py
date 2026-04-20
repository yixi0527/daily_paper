from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from app.models.article import Article, ArticleAuthor, ArticlePayload
from app.models.journal import Journal, SourceState
from app.services.content_policy import ContentPolicyService
from app.services.crossref import CrossrefClientService
from app.services.dedup import DedupService
from app.services.http import HTTPClientService
from app.services.metadata_enrichment import MetadataEnrichmentService
from app.services.normalizer import ArticleNormalizer
from app.services.pubmed import PubMedClientService
from app.services.rss_parser import RSSParserService
from app.services.types import FetchResult, NormalizedArticle, SourceSpec
from app.utils.text import payload_checksum, slugify
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class PublisherAdapter(ABC):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        http: HTTPClientService | None = None,
        rss_parser: RSSParserService | None = None,
        crossref: CrossrefClientService | None = None,
        normalizer: ArticleNormalizer | None = None,
        dedup: DedupService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http or HTTPClientService(self.settings)
        self.rss_parser = rss_parser or RSSParserService()
        self.crossref = crossref or CrossrefClientService(self.http, self.settings)
        self.normalizer = normalizer or ArticleNormalizer()
        self.dedup = dedup or DedupService()
        self.content_policy = ContentPolicyService()
        self.metadata_enricher = MetadataEnrichmentService(
            http=self.http,
            crossref=self.crossref,
            normalizer=self.normalizer,
            pubmed=PubMedClientService(self.http),
        )

    def fetch_current_issue(self, db: Session, journal: Journal) -> FetchResult:
        return self._fetch_category(db, journal, "current_issue")

    def fetch_online_first(self, db: Session, journal: Journal) -> FetchResult:
        return self._fetch_category(db, journal, "online_first")

    @abstractmethod
    def build_sources_for_category(self, journal: Journal, category: str) -> list[SourceSpec]:
        raise NotImplementedError

    def normalize_article(
        self,
        journal: Journal,
        raw_item: dict[str, Any],
        *,
        category: str,
        source_name: str,
        source_kind: str,
    ) -> NormalizedArticle | None:
        if source_kind == "rss":
            return self.normalizer.normalize_rss(
                journal, raw_item, category=category, source_name=source_name
            )
        if source_kind == "crossref":
            return self.normalizer.normalize_crossref(
                journal,
                raw_item,
                category=category,
                source_name=source_name,
            )
        raise ValueError(f"unsupported source kind: {source_kind}")

    def upsert_articles(
        self,
        db: Session,
        journal: Journal,
        articles: list[NormalizedArticle],
    ) -> dict[str, int]:
        inserted = 0
        updated = 0
        for item in articles:
            first_author = item.authors[0].full_name if item.authors else None
            doi = self.dedup.normalize_doi(item.doi)
            fallback_hash = self.dedup.build_fallback_hash(
                item.title, first_author, item.published_at
            )
            query = select(Article).where(Article.dedup_hash == fallback_hash)
            if doi:
                query = select(Article).where(
                    or_(Article.doi == doi, Article.dedup_hash == fallback_hash)
                )
            existing = db.scalar(query)
            checksum = payload_checksum(item.raw_payload or {})

            if existing is None:
                article = Article(
                    journal_id=journal.id,
                    title=item.title,
                    title_slug=slugify(item.title),
                    doi=doi,
                    url=item.url,
                    abstract=item.abstract,
                    snippet=item.snippet,
                    source_category=item.source_category,
                    article_type=item.article_type,
                    volume=item.volume,
                    issue=item.issue,
                    pages=item.pages,
                    article_number=item.article_number,
                    published_at=item.published_at,
                    online_published_at=item.online_published_at,
                    print_published_at=item.print_published_at,
                    accepted_at=item.accepted_at,
                    first_author=first_author,
                    authors_text=", ".join(author.full_name for author in item.authors) or None,
                    source_name=item.source_name,
                    source_uid=item.source_uid,
                    dedup_hash=fallback_hash,
                    raw_payload_checksum=checksum,
                    extra_metadata=item.extra_metadata,
                    last_seen_at=datetime.now(tz=UTC),
                )
                article.authors = [
                    ArticleAuthor(
                        position=index,
                        given_name=author.given_name,
                        family_name=author.family_name,
                        full_name=author.full_name,
                        affiliation=author.affiliation,
                    )
                    for index, author in enumerate(item.authors)
                ]
                article.payloads.append(
                    ArticlePayload(
                        journal_id=journal.id,
                        source_category=item.source_category,
                        source_name=item.source_name,
                        payload_format=item.payload_format,
                        payload_json=item.raw_payload,
                        payload_text=None
                        if isinstance(item.raw_payload, dict)
                        else str(item.raw_payload),
                        payload_checksum=checksum,
                    )
                )
                db.add(article)
                inserted += 1
                continue

            existing.title = item.title
            existing.title_slug = slugify(item.title)
            existing.doi = doi or existing.doi
            existing.url = item.url
            existing.abstract = item.abstract or existing.abstract
            existing.snippet = item.snippet or existing.snippet
            existing.source_category = item.source_category
            existing.article_type = item.article_type or existing.article_type
            existing.volume = item.volume or existing.volume
            existing.issue = item.issue or existing.issue
            existing.pages = item.pages or existing.pages
            existing.article_number = item.article_number or existing.article_number
            existing.published_at = item.published_at or existing.published_at
            existing.online_published_at = item.online_published_at or existing.online_published_at
            existing.print_published_at = item.print_published_at or existing.print_published_at
            existing.accepted_at = item.accepted_at or existing.accepted_at
            existing.first_author = first_author or existing.first_author
            existing.authors_text = (
                ", ".join(author.full_name for author in item.authors) or existing.authors_text
            )
            existing.source_name = item.source_name
            existing.source_uid = item.source_uid or existing.source_uid
            existing.raw_payload_checksum = checksum
            existing.extra_metadata = item.extra_metadata
            existing.last_seen_at = datetime.now(tz=UTC)
            if item.authors:
                db.query(ArticleAuthor).filter(ArticleAuthor.article_id == existing.id).delete(
                    synchronize_session=False
                )
                db.flush()
                existing.authors.extend(
                    [
                        ArticleAuthor(
                            position=index,
                            given_name=author.given_name,
                            family_name=author.family_name,
                            full_name=author.full_name,
                            affiliation=author.affiliation,
                        )
                        for index, author in enumerate(item.authors)
                    ]
                )
            if not existing.payloads or existing.payloads[-1].payload_checksum != checksum:
                existing.payloads.append(
                    ArticlePayload(
                        journal_id=journal.id,
                        source_category=item.source_category,
                        source_name=item.source_name,
                        payload_format=item.payload_format,
                        payload_json=item.raw_payload,
                        payload_text=None
                        if isinstance(item.raw_payload, dict)
                        else str(item.raw_payload),
                        payload_checksum=checksum,
                    )
                )
            updated += 1
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        return {"inserted": inserted, "updated": updated}

    def sync_category(self, db: Session, journal: Journal, category: str) -> dict[str, Any]:
        last_error: Exception | None = None
        journal_slug = journal.slug
        for source in self.build_sources_for_category(journal, category):
            state = self._get_or_create_state(db, journal, source, category)
            try:
                result = self._fetch_by_source(db, journal, source, state)
                if result.not_modified:
                    self._mark_state_checked(db, state, status_code=result.status_code)
                    return {
                        "status": "not_modified",
                        "source_name": source.name,
                        "fetched": 0,
                        "inserted": 0,
                        "updated": 0,
                    }
                if not result.items:
                    logger.warning(
                        "Source %s returned no items for %s [%s], trying fallback if available",
                        source.name,
                        journal.slug,
                        category,
                    )
                    self._mark_state_checked(db, state, status_code=result.status_code)
                    continue
                normalized = []
                for raw_item in self._filter_items(journal, result.items, category, source.kind):
                    article = self.normalize_article(
                        journal,
                        raw_item,
                        category=category,
                        source_name=source.name,
                        source_kind=source.kind,
                    )
                    if article:
                        article = self.metadata_enricher.enrich(
                            journal,
                            article,
                            source_kind=source.kind,
                        )
                    if article and self.content_policy.is_substantive(article):
                        normalized.append(article)
                counts = self.upsert_articles(db, journal, normalized)
                self._mark_state_success(db, state, result, normalized)
                return {
                    "status": "success",
                    "source_name": source.name,
                    "fetched": len(result.items),
                    "inserted": counts["inserted"],
                    "updated": counts["updated"],
                }
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.exception(
                    "Sync failed for %s [%s] via %s",
                    journal_slug,
                    category,
                    source.name,
                )
                last_error = exc
                self._mark_state_failure(db, state, exc)
                continue
        if last_error:
            raise last_error
        return {
            "status": "skipped",
            "source_name": None,
            "fetched": 0,
            "inserted": 0,
            "updated": 0,
        }

    def _fetch_category(self, db: Session, journal: Journal, category: str) -> FetchResult:
        sources = self.build_sources_for_category(journal, category)
        if not sources:
            return FetchResult(
                source_name="none",
                source_kind="none",
                source_url=None,
                items=[],
                payload_format="none",
                status_code=None,
            )
        state = self._get_or_create_state(db, journal, sources[0], category)
        return self._fetch_by_source(db, journal, sources[0], state)

    def _fetch_by_source(
        self,
        db: Session,
        journal: Journal,
        source: SourceSpec,
        state: SourceState,
    ) -> FetchResult:
        if source.kind == "rss":
            headers = {}
            if state.etag:
                headers["If-None-Match"] = state.etag
            if state.last_modified:
                headers["If-Modified-Since"] = state.last_modified
            response = self.http.get(source.url or "", headers=headers or None)
            if response.status_code == 304:
                return FetchResult(
                    source_name=source.name,
                    source_kind=source.kind,
                    source_url=source.url,
                    items=[],
                    payload_format="rss",
                    status_code=304,
                    etag=state.etag,
                    last_modified=state.last_modified,
                    not_modified=True,
                )
            items = self.rss_parser.parse(response.content)
            return FetchResult(
                source_name=source.name,
                source_kind=source.kind,
                source_url=source.url,
                items=items,
                payload_format="rss",
                status_code=response.status_code,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )

        if source.kind == "crossref":
            items: list[dict[str, Any]] = []
            cursor = state.cursor or "*"
            last_headers = {}
            for _ in range(self.settings.sync_max_pages):
                page = self.crossref.fetch_recent(source.metadata.get("filters", {}), cursor=cursor)
                page_items = page["items"]
                items.extend(page_items)
                last_headers = page.get("headers", {})
                next_cursor = page.get("next_cursor")
                if not page_items or not next_cursor or next_cursor == cursor:
                    state.cursor = None
                    db.commit()
                    break
                cursor = next_cursor
                state.cursor = cursor
                state.last_checked_at = datetime.now(tz=UTC)
                db.commit()
                if len(page_items) < 100:
                    break
            return FetchResult(
                source_name=source.name,
                source_kind=source.kind,
                source_url=page.get("request_url"),
                items=items,
                payload_format="json",
                status_code=page.get("status_code"),
                etag=last_headers.get("ETag"),
                last_modified=last_headers.get("Last-Modified"),
                request_meta={"next_cursor": cursor},
            )

        raise ValueError(f"Unknown source kind: {source.kind}")

    def _filter_items(
        self,
        journal: Journal,
        items: Iterable[dict[str, Any]],
        category: str,
        source_kind: str,
    ) -> list[dict[str, Any]]:
        if source_kind != "crossref":
            return list(items)
        filtered = []
        for item in items:
            has_issue = bool(item.get("issue") or item.get("volume") or item.get("published-print"))
            has_online = bool(item.get("published-online") or item.get("published"))
            if category == "current_issue" and has_issue:
                filtered.append(item)
            elif category == "online_first" and has_online and not has_issue:
                filtered.append(item)
        return filtered or list(items)

    def _get_or_create_state(
        self,
        db: Session,
        journal: Journal,
        source: SourceSpec,
        category: str,
    ) -> SourceState:
        state = db.scalar(
            select(SourceState).where(
                SourceState.journal_id == journal.id,
                SourceState.source_category == category,
                SourceState.source_name == source.name,
            )
        )
        if state:
            return state
        state = SourceState(
            journal_id=journal.id,
            source_category=category,
            source_name=source.name,
            source_url=source.url,
        )
        db.add(state)
        db.commit()
        db.refresh(state)
        return state

    def _mark_state_checked(
        self, db: Session, state: SourceState, *, status_code: int | None
    ) -> None:
        state.last_checked_at = datetime.now(tz=UTC)
        state.last_status_code = status_code
        db.commit()

    def _mark_state_success(
        self,
        db: Session,
        state: SourceState,
        result: FetchResult,
        articles: list[NormalizedArticle],
    ) -> None:
        state.source_url = result.source_url
        state.etag = result.etag or state.etag
        state.last_modified = result.last_modified or state.last_modified
        state.last_status_code = result.status_code
        state.last_checked_at = datetime.now(tz=UTC)
        state.last_success_at = datetime.now(tz=UTC)
        state.last_error = None
        state.consecutive_failures = 0
        state.cursor = None
        timestamps = [article.published_at for article in articles if article.published_at]
        if timestamps:
            state.latest_seen_published_at = max(timestamps)
        db.commit()

    def _mark_state_failure(self, db: Session, state: SourceState, error: Exception) -> None:
        state.last_checked_at = datetime.now(tz=UTC)
        state.last_error = str(error)
        state.consecutive_failures += 1
        db.commit()
