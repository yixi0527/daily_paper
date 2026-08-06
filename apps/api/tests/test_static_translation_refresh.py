import json
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from app.services.article_registry import text_sha256
from app.services.static_translation_refresh import refresh_static_translation_payload

from scripts.pages_deploy import ZERO_SHA, deployment_mode


def write_registry(path: Path, *, title_hash: str | None = None) -> None:
    payload = {
        "schema_version": 1,
        "updated_at": "2026-08-06T05:00:00+00:00",
        "articles": {
            "doi:10.1000/test": {
                "doi": "10.1000/test",
                "journal_slug": "test-journal",
                "title": "A test article",
                "acquired_at": "2026-08-06T01:00:00+00:00",
                "source_title_sha256": title_hash or text_sha256("A test article"),
                "source_abstract_sha256": text_sha256("An abstract."),
                "source_abstract": "abstract",
                "title_zh": "测试文章",
                "abstract_zh": "摘要。",
                "translation_model": "gpt-5.3-codex-spark",
                "translated_at": "2026-08-06T05:00:00+00:00",
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def site_data() -> dict:
    article = {
        "article_key": "doi:10.1000/test",
        "title": "A test article",
        "title_zh": None,
        "doi": "10.1000/test",
        "abstract": "An abstract.",
        "abstract_zh": None,
        "snippet": None,
        "acquired_at": "2026-08-06T01:00:00+00:00",
        "translation_model": None,
        "translated_at": None,
        "journal": {"slug": "test-journal"},
    }
    return {
        "articles": [article],
        "journals": [{"slug": "test-journal"}],
        "dashboard": {"latest_articles": [dict(article)]},
        "sync_runs": [],
    }


def metadata() -> dict:
    return {
        "schema_version": 1,
        "generated_at": "2026-08-06T04:00:00+00:00",
        "article_count": 1,
        "journal_count": 1,
        "sync": {
            "run_id": "sync-1",
            "status": "success",
            "started_at": "2026-08-06T01:00:00+00:00",
            "finished_at": "2026-08-06T03:00:00+00:00",
            "total_journals": 1,
            "total_processed": 1,
            "total_failed": 0,
        },
        "deployment": {
            "source_revision": "a" * 40,
            "source_event": "schedule",
            "workflow_run_id": "100",
        },
    }


def refresh(registry_path: Path) -> tuple[dict, dict]:
    return refresh_static_translation_payload(
        site_data(),
        metadata(),
        registry_path=registry_path,
        source_revision="b" * 40,
        source_event="push",
        workflow_run_id="200",
        expected_sync_date=date(2026, 8, 6),
        timezone=ZoneInfo("Asia/Shanghai"),
        generated_at=datetime(2026, 8, 6, 5, 5, tzinfo=UTC),
    )


def test_translation_only_mode_requires_exact_registry_change() -> None:
    assert deployment_mode(
        event_name="push",
        before_sha="a" * 40,
        changed_paths=["packages/shared/data/article_registry.json"],
    ) == "translations"
    assert deployment_mode(
        event_name="push",
        before_sha="a" * 40,
        changed_paths=["packages/shared/data/article_registry.json", "README.md"],
    ) == "full"
    assert deployment_mode(
        event_name="schedule",
        before_sha="",
        changed_paths=[],
    ) == "full"
    assert deployment_mode(
        event_name="push",
        before_sha=ZERO_SHA,
        changed_paths=[],
    ) == "full"


def test_translation_refresh_updates_full_and_dashboard_articles(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    write_registry(registry_path)

    refreshed_site, refreshed_metadata = refresh(registry_path)

    assert refreshed_site["articles"][0]["title_zh"] == "测试文章"
    assert refreshed_site["articles"][0]["abstract_zh"] == "摘要。"
    assert refreshed_site["dashboard"]["latest_articles"][0]["title_zh"] == "测试文章"
    assert refreshed_metadata["sync"] == metadata()["sync"]
    assert refreshed_metadata["deployment"] == {
        "source_revision": "b" * 40,
        "source_event": "push",
        "workflow_run_id": "200",
    }
    assert refreshed_metadata["translation_refresh"]["base_deployment"] == metadata()[
        "deployment"
    ]


def test_translation_refresh_rejects_stale_registry_entry(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    write_registry(registry_path, title_hash=text_sha256("Old title"))

    with pytest.raises(ValueError, match="Current title translation missing"):
        refresh(registry_path)


def test_translation_refresh_requires_successful_current_sync(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    write_registry(registry_path)
    stale_metadata = metadata()
    stale_metadata["sync"]["status"] = "partial_success"

    with pytest.raises(ValueError, match="Deployed sync status must be success"):
        refresh_static_translation_payload(
            site_data(),
            stale_metadata,
            registry_path=registry_path,
            source_revision="b" * 40,
            source_event="push",
            workflow_run_id="200",
            expected_sync_date=date(2026, 8, 6),
            timezone=ZoneInfo("Asia/Shanghai"),
            generated_at=datetime(2026, 8, 6, 5, 5, tzinfo=UTC),
        )
