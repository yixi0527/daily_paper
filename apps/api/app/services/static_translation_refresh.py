from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.services.article_registry import ArticleRegistryService, parse_registry_datetime
from app.services.deployment_metadata import require_object, validate_metadata

TRANSLATION_FIELDS = (
    "title_zh",
    "abstract_zh",
    "translation_model",
    "translated_at",
)


def require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def validate_translation_base(
    metadata: dict[str, Any],
    *,
    expected_sync_date: date,
    timezone: ZoneInfo,
) -> tuple[dict[str, str], dict[str, Any]]:
    deployment = require_object(metadata.get("deployment"), "deployment")
    base_deployment = {
        "workflow_run_id": require_nonempty_string(
            deployment.get("workflow_run_id"),
            "deployment.workflow_run_id",
        ),
        "source_revision": require_nonempty_string(
            deployment.get("source_revision"),
            "deployment.source_revision",
        ),
        "source_event": require_nonempty_string(
            deployment.get("source_event"),
            "deployment.source_event",
        ),
    }
    summary = validate_metadata(
        metadata,
        expected_workflow_run_id=base_deployment["workflow_run_id"],
        expected_source_revision=base_deployment["source_revision"],
        expected_source_event=base_deployment["source_event"],
        expected_sync_date=expected_sync_date,
        timezone=timezone,
    )
    return base_deployment, summary


def refresh_article(
    article: dict[str, Any],
    *,
    registry: ArticleRegistryService,
) -> dict[str, Any]:
    title = require_nonempty_string(article.get("title"), "article.title")
    journal = require_object(article.get("journal"), "article.journal")
    journal_slug = require_nonempty_string(journal.get("slug"), "article.journal.slug")
    acquired_at = parse_registry_datetime(
        require_nonempty_string(article.get("acquired_at"), "article.acquired_at")
    )
    record = registry.resolve(
        doi=article.get("doi"),
        journal_slug=journal_slug,
        title=title,
        abstract=article.get("abstract"),
        snippet=article.get("snippet"),
        first_seen_at=acquired_at,
    )
    exported_key = require_nonempty_string(article.get("article_key"), "article.article_key")
    if exported_key != record.article_key:
        raise ValueError(
            f"Article key mismatch: exported={exported_key} registry={record.article_key}"
        )
    if not record.title_zh:
        raise ValueError(f"Current title translation missing for {record.article_key}")
    source_abstract = article.get("abstract") or article.get("snippet")
    if source_abstract is not None and not record.abstract_zh:
        raise ValueError(f"Current abstract translation missing for {record.article_key}")
    if not record.translation_model:
        raise ValueError(f"Translation model missing for {record.article_key}")
    if record.translated_at is None:
        raise ValueError(f"Translation timestamp missing for {record.article_key}")

    refreshed = dict(article)
    refreshed["title_zh"] = record.title_zh
    refreshed["abstract_zh"] = record.abstract_zh
    refreshed["translation_model"] = record.translation_model
    refreshed["translated_at"] = record.translated_at.isoformat()
    return refreshed


def refresh_static_translation_payload(
    site_data: dict[str, Any],
    metadata: dict[str, Any],
    *,
    registry_path: Path,
    source_revision: str,
    source_event: str,
    workflow_run_id: str,
    expected_sync_date: date,
    timezone: ZoneInfo,
    generated_at: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must include a timezone offset")
    deployment = {
        "source_revision": require_nonempty_string(source_revision, "source_revision"),
        "source_event": require_nonempty_string(source_event, "source_event"),
        "workflow_run_id": require_nonempty_string(workflow_run_id, "workflow_run_id"),
    }
    base_deployment, base_summary = validate_translation_base(
        metadata,
        expected_sync_date=expected_sync_date,
        timezone=timezone,
    )
    refreshed_site_data = deepcopy(site_data)
    articles = require_list(refreshed_site_data.get("articles"), "site_data.articles")
    journals = require_list(refreshed_site_data.get("journals"), "site_data.journals")
    if not articles:
        raise ValueError("site_data.articles must not be empty")
    if not journals:
        raise ValueError("site_data.journals must not be empty")
    if base_summary["article_count"] != len(articles):
        raise ValueError(
            "Base metadata article_count mismatch: "
            f"metadata={base_summary['article_count']} site_data={len(articles)}"
        )
    if base_summary["journal_count"] != len(journals):
        raise ValueError(
            "Base metadata journal_count mismatch: "
            f"metadata={base_summary['journal_count']} site_data={len(journals)}"
        )

    registry = ArticleRegistryService(registry_path=registry_path)
    refreshed_articles: list[dict[str, Any]] = []
    articles_by_key: dict[str, dict[str, Any]] = {}
    for raw_article in articles:
        article = require_object(raw_article, "site_data.articles[]")
        refreshed = refresh_article(article, registry=registry)
        article_key = refreshed["article_key"]
        if article_key in articles_by_key:
            raise ValueError(f"Duplicate article key in site data: {article_key}")
        refreshed_articles.append(refreshed)
        articles_by_key[article_key] = refreshed
    refreshed_site_data["articles"] = refreshed_articles

    dashboard = require_object(refreshed_site_data.get("dashboard"), "site_data.dashboard")
    latest_articles = require_list(
        dashboard.get("latest_articles"),
        "site_data.dashboard.latest_articles",
    )
    refreshed_latest: list[dict[str, Any]] = []
    for raw_article in latest_articles:
        dashboard_article = require_object(
            raw_article,
            "site_data.dashboard.latest_articles[]",
        )
        article_key = require_nonempty_string(
            dashboard_article.get("article_key"),
            "site_data.dashboard.latest_articles[].article_key",
        )
        canonical = articles_by_key.get(article_key)
        if canonical is None:
            raise ValueError(f"Dashboard article missing from full article list: {article_key}")
        refreshed_dashboard_article = dict(dashboard_article)
        for field in TRANSLATION_FIELDS:
            refreshed_dashboard_article[field] = canonical[field]
        refreshed_latest.append(refreshed_dashboard_article)
    dashboard["latest_articles"] = refreshed_latest

    refreshed_metadata = deepcopy(metadata)
    refreshed_metadata["generated_at"] = generated_at.isoformat()
    refreshed_metadata["article_count"] = len(refreshed_articles)
    refreshed_metadata["journal_count"] = len(journals)
    refreshed_metadata["deployment"] = deployment
    refreshed_metadata["translation_refresh"] = {
        "base_deployment": base_deployment,
        "refreshed_at": generated_at.isoformat(),
    }
    return refreshed_site_data, refreshed_metadata
