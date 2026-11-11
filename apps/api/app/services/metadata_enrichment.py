from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape
from urllib.parse import urljoin

import httpx
from app.core.logging import get_logger
from app.models.journal import Journal
from app.services.crossref import CrossrefClientService
from app.services.http import HTTPClientService, TransientHTTPError
from app.services.normalizer import ArticleNormalizer
from app.services.pubmed import PubMedClientService
from app.services.types import NormalizedArticle
from app.utils.text import compact_text, first_meaningful_text

logger = get_logger(__name__)

META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
META_ATTR_RE = re.compile(r'([a-zA-Z_:.-]+)\s*=\s*(["\'])(.*?)\2', re.DOTALL)
ONLINE_HISTORY_RE = re.compile(
    r"Published\s+online\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", re.IGNORECASE
)


class MetadataEnrichmentService:
    def __init__(
        self,
        *,
        http: HTTPClientService,
        crossref: CrossrefClientService,
        normalizer: ArticleNormalizer,
        pubmed: PubMedClientService,
    ) -> None:
        self.http = http
        self.crossref = crossref
        self.normalizer = normalizer
        self.pubmed = pubmed

    def enrich(
        self,
        journal: Journal,
        article: NormalizedArticle,
        *,
        source_kind: str,
    ) -> NormalizedArticle:
        if article.doi and self._needs_crossref_enrichment(article, source_kind=source_kind):
            crossref_payload = self.crossref.fetch_work(article.doi)
            if crossref_payload:
                normalized = self.normalizer.normalize_crossref(
                    journal,
                    crossref_payload,
                    category=article.source_category,
                    source_name="crossref",
                )
                if normalized:
                    article = self._merge(article, normalized)

        if not article.abstract or not article.online_published_at:
            metadata = self.fetch_publisher_metadata(self.publisher_url(article))
            if not article.abstract and metadata.get("abstract"):
                article.abstract = metadata["abstract"]
                article.snippet = compact_text(article.abstract)
            if not article.online_published_at:
                article.extra_metadata = {
                    **(article.extra_metadata or {}),
                    "publisher_online_date": {k: v for k, v in metadata.items() if k != "abstract"},
                }
                if metadata.get("date"):
                    article.online_published_at = datetime.fromisoformat(metadata["date"])
                    article.published_at = article.online_published_at
        if not article.abstract:
            pubmed_metadata = self.pubmed.fetch_metadata(doi=article.doi, title=article.title)
            if pubmed_metadata:
                if pubmed_metadata.get("abstract"):
                    article.abstract = pubmed_metadata["abstract"]
                    article.snippet = compact_text(article.abstract)
                publication_types = pubmed_metadata.get("publication_types", [])
                specific_type = next(
                    (
                        item
                        for item in publication_types
                        if item.lower() not in {"journal article", "research support, non-u.s. gov't"}
                    ),
                    None,
                )
                if (
                    specific_type
                    and (not article.article_type or article.article_type.lower() == "journal-article")
                ):
                    article.article_type = specific_type
        elif not article.snippet:
            article.snippet = compact_text(article.abstract)

        return article

    @staticmethod
    def publisher_url(article: NormalizedArticle) -> str:
        evidence = (article.extra_metadata or {}).get("publisher_online_date")
        if evidence and evidence.get("status") == "found":
            return evidence["url"]
        payload = article.raw_payload or {}
        return payload.get("resource", {}).get("primary", {}).get("URL") or article.url

    def fetch_publisher_metadata(self, url: str) -> dict:
        checked_at = datetime.now(UTC).isoformat()
        try:
            for _ in range(4):
                response = self.http.get(url, headers={"Accept": "text/html,application/xhtml+xml"})
                response.raise_for_status()
                refresh = next(
                    (attrs.get("content") for attrs in self._meta_attributes(response.text)
                     if attrs.get("http-equiv", "").lower() == "refresh"),
                    None,
                )
                if not refresh:
                    break
                url = urljoin(str(response.url), refresh.split(";", 1)[1].split("=", 1)[1].strip(" '\""))
            else:
                raise httpx.TooManyRedirects("Publisher HTML refresh limit exceeded", request=response.request)
        except (httpx.HTTPError, TransientHTTPError) as error:
            logger.exception("Publisher metadata request failed for %s", url)
            return {"status": "request_failed", "url": url, "checked_at": checked_at, "error": str(error)}
        metadata = self.extract_publisher_metadata(response.text)
        return {**metadata, "url": str(response.url), "checked_at": checked_at}

    @staticmethod
    def _meta_attributes(html: str) -> list[dict[str, str]]:
        return [
            {key.lower(): unescape(value.strip()) for key, _, value in META_ATTR_RE.findall(tag)}
            for tag in META_TAG_RE.findall(html)
        ]

    def extract_publisher_metadata(self, html: str) -> dict:
        metadata = {"status": "not_exposed", "abstract": self._extract_meta_description(html)}
        for attrs in self._meta_attributes(html):
            key = (attrs.get("name") or attrs.get("property") or "").lower()
            if key == "citation_online_date" and attrs.get("content"):
                value = attrs["content"]
                online = datetime.strptime(value.replace("/", "-"), "%Y-%m-%d").replace(tzinfo=UTC)
                return {**metadata, "status": "found", "date": online.isoformat(), "field": key, "value": value}
        text = unescape(re.sub(r"<[^>]+>", " ", html))
        history_section = re.search(r"Publication\s+History\s*:[\s\S]{0,500}", text, re.IGNORECASE)
        history = ONLINE_HISTORY_RE.search(history_section[0]) if history_section else None
        if history:
            value = " ".join(history[1].replace(",", "").split())
            online = datetime.strptime(value, "%B %d %Y").replace(tzinfo=UTC)
            return {**metadata, "status": "found", "date": online.isoformat(), "field": "Published online", "value": history[0]}
        return metadata

    def _extract_meta_description(self, html: str) -> str | None:
        candidates: list[str | None] = []
        for attrs in self._meta_attributes(html):
            key = (attrs.get("name") or attrs.get("property") or "").lower()
            if key not in {
                "citation_abstract",
                "dc.description",
                "description",
                "og:description",
                "twitter:description",
            }:
                continue
            candidates.append(attrs.get("content"))
        return first_meaningful_text(candidates)

    def _merge(
        self, base: NormalizedArticle, fallback: NormalizedArticle
    ) -> NormalizedArticle:
        if not base.abstract and fallback.abstract:
            base.abstract = fallback.abstract
        if not base.snippet and fallback.snippet:
            base.snippet = fallback.snippet
        if (not base.article_type or base.article_type.lower() == "journal-article") and fallback.article_type:
            base.article_type = fallback.article_type
        if not base.authors and fallback.authors:
            base.authors = fallback.authors
        if not base.volume and fallback.volume:
            base.volume = fallback.volume
        if not base.issue and fallback.issue:
            base.issue = fallback.issue
        if not base.pages and fallback.pages:
            base.pages = fallback.pages
        if not base.published_at and fallback.published_at:
            base.published_at = fallback.published_at
        if not base.online_published_at and fallback.online_published_at:
            base.online_published_at = fallback.online_published_at
        if not base.print_published_at and fallback.print_published_at:
            base.print_published_at = fallback.print_published_at
        return base

    @staticmethod
    def _needs_crossref_enrichment(
        article: NormalizedArticle, *, source_kind: str
    ) -> bool:
        if source_kind == "crossref":
            return False
        return (
            not article.abstract
            or not article.authors
            or not article.article_type
            or article.article_type.lower() == "journal-article"
        )
