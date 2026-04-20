from __future__ import annotations

import re

from app.models.journal import Journal
from app.services.crossref import CrossrefClientService
from app.services.http import HTTPClientService
from app.services.normalizer import ArticleNormalizer
from app.services.pubmed import PubMedClientService
from app.services.types import NormalizedArticle
from app.utils.text import compact_text, first_meaningful_text

META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
META_ATTR_RE = re.compile(r'([a-zA-Z_:.-]+)\s*=\s*(["\'])(.*?)\2', re.DOTALL)


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

        if not article.abstract:
            meta_abstract = self.fetch_meta_abstract(article.url)
            if meta_abstract:
                article.abstract = meta_abstract
                article.snippet = compact_text(meta_abstract)
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

    def fetch_meta_abstract(self, url: str) -> str | None:
        try:
            response = self.http.get(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        except Exception:  # noqa: BLE001
            return None
        if response.status_code != 200:
            return None
        return self._extract_meta_description(response.text)

    def _extract_meta_description(self, html: str) -> str | None:
        candidates: list[str | None] = []
        for tag in META_TAG_RE.findall(html):
            attrs = {
                key.lower(): value.strip()
                for key, _, value in META_ATTR_RE.findall(tag)
                if value.strip()
            }
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

    def _needs_crossref_enrichment(
        self, article: NormalizedArticle, *, source_kind: str
    ) -> bool:
        if source_kind != "crossref" and (
            not article.abstract
            or not article.authors
            or not article.article_type
            or article.article_type.lower() == "journal-article"
        ):
            return True
        return source_kind == "crossref" and not article.abstract
