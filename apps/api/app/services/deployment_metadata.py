from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def require_integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone offset")
    return parsed


def validate_metadata(
    payload: dict[str, Any],
    *,
    expected_workflow_run_id: str,
    expected_source_revision: str,
    expected_source_event: str,
    expected_sync_date: date,
    timezone: ZoneInfo,
    require_complete_translations: bool = False,
    max_site_data_bytes: int | None = None,
) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError("metadata schema_version must be 1")

    deployment = require_object(payload.get("deployment"), "deployment")
    if deployment.get("workflow_run_id") != expected_workflow_run_id:
        raise ValueError(
            "Deployment workflow_run_id mismatch: "
            f"expected={expected_workflow_run_id} "
            f"actual={deployment.get('workflow_run_id')}"
        )
    if deployment.get("source_revision") != expected_source_revision:
        raise ValueError(
            "Deployment source_revision mismatch: "
            f"expected={expected_source_revision} "
            f"actual={deployment.get('source_revision')}"
        )
    if deployment.get("source_event") != expected_source_event:
        raise ValueError(
            "Deployment source_event mismatch: "
            f"expected={expected_source_event} actual={deployment.get('source_event')}"
        )

    sync = require_object(payload.get("sync"), "sync")
    if sync.get("status") != "success":
        raise ValueError(f"Deployed sync status must be success: {sync.get('status')}")
    total_journals = require_integer(sync.get("total_journals"), "sync.total_journals")
    total_processed = require_integer(sync.get("total_processed"), "sync.total_processed")
    total_failed = require_integer(sync.get("total_failed"), "sync.total_failed")
    if total_journals < 1:
        raise ValueError("sync.total_journals must be positive")
    if total_processed != total_journals:
        raise ValueError(
            "Deployed sync did not process every journal: "
            f"processed={total_processed} journals={total_journals}"
        )
    if total_failed != 0:
        raise ValueError(f"Deployed sync contains failed journals: {total_failed}")

    sync_finished_at = parse_timestamp(sync.get("finished_at"), "sync.finished_at")
    generated_at = parse_timestamp(payload.get("generated_at"), "generated_at")
    if generated_at < sync_finished_at:
        raise ValueError("generated_at precedes sync.finished_at")
    actual_sync_date = sync_finished_at.astimezone(timezone).date()
    if actual_sync_date != expected_sync_date:
        raise ValueError(
            "Deployed sync date mismatch: "
            f"expected={expected_sync_date.isoformat()} actual={actual_sync_date.isoformat()}"
        )

    article_count = require_integer(payload.get("article_count"), "article_count")
    journal_count = require_integer(payload.get("journal_count"), "journal_count")
    site_data_bytes = require_integer(payload.get("site_data_bytes"), "site_data_bytes")
    if article_count < 1:
        raise ValueError("article_count must be positive")
    if journal_count < 1:
        raise ValueError("journal_count must be positive")
    if site_data_bytes < 1:
        raise ValueError("site_data_bytes must be positive")
    if max_site_data_bytes is not None and site_data_bytes > max_site_data_bytes:
        raise ValueError(
            "site_data_bytes exceeds the allowed maximum: "
            f"actual={site_data_bytes} maximum={max_site_data_bytes}"
        )

    translations = require_object(payload.get("translations"), "translations")
    translation_total = require_integer(
        translations.get("total_articles"),
        "translations.total_articles",
    )
    translation_complete = require_integer(
        translations.get("complete_articles"),
        "translations.complete_articles",
    )
    translation_pending = require_integer(
        translations.get("pending_articles"),
        "translations.pending_articles",
    )
    if min(translation_total, translation_complete, translation_pending) < 0:
        raise ValueError("translation counts must be non-negative")
    if translation_total != article_count:
        raise ValueError(
            "Translation total does not match article_count: "
            f"translations={translation_total} articles={article_count}"
        )
    if translation_complete + translation_pending != translation_total:
        raise ValueError(
            "Translation counts are inconsistent: "
            f"complete={translation_complete} pending={translation_pending} "
            f"total={translation_total}"
        )
    if require_complete_translations and translation_pending != 0:
        raise ValueError(
            "Deployed translations are incomplete: "
            f"pending_articles={translation_pending}"
        )

    return {
        "workflow_run_id": expected_workflow_run_id,
        "source_revision": expected_source_revision,
        "source_event": expected_source_event,
        "sync_run_id": sync.get("run_id"),
        "sync_finished_at": sync_finished_at.isoformat(),
        "article_count": article_count,
        "journal_count": journal_count,
        "site_data_bytes": site_data_bytes,
        "complete_translations": translation_complete,
        "pending_translations": translation_pending,
    }
