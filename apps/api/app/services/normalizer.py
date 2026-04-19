from __future__ import annotations

from typing import Any

from app.models.journal import Journal
from app.services.types import NormalizedArticle, NormalizedAuthor
from app.utils.dates import parse_crossref_date_parts, parse_datetime
from app.utils.text import compact_text, strip_html


class ArticleNormalizer:
    def normalize_rss(
        self,
        journal: Journal,
        payload: dict[str, Any],
        *,
        category: str,
        source_name: str,
    ) -> NormalizedArticle | None:
        title = payload.get("title") or payload.get("dc_title")
        link = payload.get("link")
        if not title or not link:
            return None
        authors = self._normalize_rss_authors(payload)
        abstract = strip_html(
            payload.get("summary") or payload.get("content", [{}])[0].get("value")
        )
        doi = self._extract_rss_doi(payload)
        start_page = payload.get("prism_startingpage")
        end_page = payload.get("prism_endingpage")
        pages = None
        if start_page and end_page:
            pages = f"{start_page}-{end_page}"
        elif start_page:
            pages = str(start_page)
        published_at = (
            parse_datetime(payload.get("published"))
            or parse_datetime(payload.get("updated"))
            or parse_datetime(payload.get("prism_publicationdate"))
            or parse_datetime(payload.get("dc_date"))
        )
        return NormalizedArticle(
            title=title.strip(),
            url=link,
            doi=doi,
            abstract=abstract,
            snippet=compact_text(abstract or strip_html(payload.get("description"))),
            source_category=category,
            source_name=source_name,
            source_uid=str(payload.get("id") or payload.get("guid") or link),
            authors=authors,
            article_type=payload.get("prism_section")
            or payload.get("category")
            or self._first_tag(payload),
            volume=str(payload.get("prism_volume") or "") or None,
            issue=str(payload.get("prism_number") or payload.get("prism_issueidentifier") or "")
            or None,
            pages=pages,
            article_number=str(payload.get("prism_issueidentifier") or "") or None,
            published_at=published_at,
            online_published_at=published_at if category == "online_first" else None,
            print_published_at=published_at if category == "current_issue" else None,
            extra_metadata={
                "journal_name": journal.journal_name,
                "rss_tags": payload.get("tags"),
            },
            raw_payload=payload,
            payload_format="json",
        )

    def normalize_crossref(
        self,
        journal: Journal,
        payload: dict[str, Any],
        *,
        category: str,
        source_name: str,
    ) -> NormalizedArticle | None:
        titles = payload.get("title") or []
        title = titles[0].strip() if titles else None
        link = payload.get("URL")
        if not title or not link:
            return None
        authors = self._normalize_crossref_authors(payload.get("author", []))
        abstract = strip_html(payload.get("abstract"))
        online_date = parse_crossref_date_parts(
            payload.get("published-online", {}).get("date-parts")
        )
        print_date = parse_crossref_date_parts(payload.get("published-print", {}).get("date-parts"))
        issued_date = parse_crossref_date_parts(payload.get("issued", {}).get("date-parts"))
        published_at = online_date or print_date or issued_date
        return NormalizedArticle(
            title=title,
            url=link,
            doi=payload.get("DOI"),
            abstract=abstract,
            snippet=compact_text(abstract),
            source_category=category,
            source_name=source_name,
            source_uid=payload.get("DOI") or link,
            authors=authors,
            article_type=payload.get("subtype") or payload.get("type"),
            volume=str(payload.get("volume") or "") or None,
            issue=str(payload.get("issue") or "") or None,
            pages=payload.get("page"),
            article_number=str(payload.get("article-number") or "") or None,
            published_at=published_at,
            online_published_at=online_date,
            print_published_at=print_date,
            accepted_at=parse_crossref_date_parts(payload.get("accepted", {}).get("date-parts")),
            extra_metadata={
                "container_title": payload.get("container-title"),
                "publisher": payload.get("publisher"),
                "relation": payload.get("relation"),
            },
            raw_payload=payload,
            payload_format="json",
        )

    def _normalize_rss_authors(self, payload: dict[str, Any]) -> list[NormalizedAuthor]:
        raw_authors = payload.get("authors") or []
        authors = []
        for raw in raw_authors:
            name = raw.get("name") if isinstance(raw, dict) else str(raw)
            if not name:
                continue
            authors.append(NormalizedAuthor(full_name=name.strip()))
        if authors:
            return authors
        creator = payload.get("author") or payload.get("dc_creator")
        if isinstance(creator, list):
            return [
                NormalizedAuthor(full_name=str(item).strip())
                for item in creator
                if str(item).strip()
            ]
        if creator:
            return [NormalizedAuthor(full_name=str(creator).strip())]
        return []

    def _normalize_crossref_authors(
        self, raw_authors: list[dict[str, Any]]
    ) -> list[NormalizedAuthor]:
        authors = []
        for raw in raw_authors:
            given = raw.get("given")
            family = raw.get("family")
            full_name = " ".join(part for part in [given, family] if part).strip()
            if not full_name:
                full_name = raw.get("name") or "Unknown"
            affiliation = None
            affiliations = raw.get("affiliation") or []
            if affiliations:
                affiliation = affiliations[0].get("name")
            authors.append(
                NormalizedAuthor(
                    full_name=full_name,
                    given_name=given,
                    family_name=family,
                    affiliation=affiliation,
                )
            )
        return authors

    def _extract_rss_doi(self, payload: dict[str, Any]) -> str | None:
        for key in ("prism_doi", "dc_identifier", "identifier"):
            value = payload.get(key)
            if not value:
                continue
            if isinstance(value, list):
                for item in value:
                    parsed = self._extract_single_doi(item)
                    if parsed:
                        return parsed
            parsed = self._extract_single_doi(value)
            if parsed:
                return parsed
        return None

    def _extract_single_doi(self, value: Any) -> str | None:
        raw = str(value).strip()
        if not raw:
            return None
        if raw.lower().startswith("doi:"):
            return raw[4:].strip()
        if raw.lower().startswith("10."):
            return raw
        return None

    def _first_tag(self, payload: dict[str, Any]) -> str | None:
        tags = payload.get("tags") or []
        if not tags:
            return None
        first = tags[0]
        if isinstance(first, dict):
            return first.get("term") or first.get("label")
        return str(first)
