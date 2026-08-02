from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.settings import Settings, get_settings

DISPLAY_DATE_CUTOFF = datetime(2026, 7, 1, tzinfo=UTC)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    normalized = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized.removeprefix(prefix)
    return normalized or None


def normalized_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def text_sha256(value: str | None) -> str:
    normalized = normalized_text(value or "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_registry_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def build_article_key(*, doi: str | None, journal_slug: str, title: str) -> str:
    normalized_doi = normalize_doi(doi)
    if normalized_doi:
        return f"doi:{normalized_doi}"
    identity = f"{journal_slug.strip().lower()}\n{normalized_text(title).lower()}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"title:{digest}"


def display_date(*, published_at: datetime | None, acquired_at: datetime) -> datetime:
    if published_at is None:
        return acquired_at
    comparable_published = (
        published_at.replace(tzinfo=UTC) if published_at.tzinfo is None else published_at
    )
    if comparable_published > DISPLAY_DATE_CUTOFF:
        return acquired_at
    return published_at


@dataclass(frozen=True, slots=True)
class RegistryRecord:
    article_key: str
    acquired_at: datetime
    title_zh: str | None
    abstract_zh: str | None
    translation_model: str | None
    translated_at: datetime | None


class ArticleRegistryService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        registry_path: Path | None = None,
    ) -> None:
        configured_path = (settings or get_settings()).article_registry_path
        self.registry_path = registry_path or configured_path
        self._records = self._load_records()

    def resolve(
        self,
        *,
        doi: str | None,
        journal_slug: str,
        title: str,
        abstract: str | None,
        snippet: str | None,
        first_seen_at: datetime,
    ) -> RegistryRecord:
        article_key = build_article_key(doi=doi, journal_slug=journal_slug, title=title)
        entry = self._records.get(article_key)
        if entry is None:
            return RegistryRecord(
                article_key=article_key,
                acquired_at=first_seen_at,
                title_zh=None,
                abstract_zh=None,
                translation_model=None,
                translated_at=None,
            )

        source_abstract = abstract or snippet
        source_matches = (
            entry["source_title_sha256"] == text_sha256(title)
            and entry["source_abstract_sha256"] == text_sha256(source_abstract)
        )
        title_zh = entry["title_zh"] if source_matches else None
        abstract_zh = entry["abstract_zh"] if source_matches else None
        translation_model = entry["translation_model"] if source_matches else None
        translated_at = (
            parse_registry_datetime(entry["translated_at"])
            if source_matches and entry["translated_at"]
            else None
        )
        return RegistryRecord(
            article_key=article_key,
            acquired_at=parse_registry_datetime(entry["acquired_at"]),
            title_zh=title_zh,
            abstract_zh=abstract_zh,
            translation_model=translation_model,
            translated_at=translated_at,
        )

    def _load_records(self) -> dict[str, dict[str, Any]]:
        if not self.registry_path.is_file():
            raise FileNotFoundError(self.registry_path)
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("Article registry schema_version must be 1")
        articles = payload.get("articles")
        if not isinstance(articles, dict):
            raise ValueError("Article registry articles must be an object")
        return articles


@lru_cache(maxsize=1)
def get_article_registry() -> ArticleRegistryService:
    return ArticleRegistryService()
