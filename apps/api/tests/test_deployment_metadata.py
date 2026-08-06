from datetime import date
from zoneinfo import ZoneInfo

import pytest
from app.services.deployment_metadata import validate_metadata


def deployment_metadata() -> dict:
    return {
        "schema_version": 1,
        "generated_at": "2026-08-06T02:05:00+00:00",
        "article_count": 42,
        "journal_count": 26,
        "sync": {
            "run_id": "sync-run-id",
            "status": "success",
            "started_at": "2026-08-06T00:50:00+00:00",
            "finished_at": "2026-08-06T02:00:00+00:00",
            "total_journals": 26,
            "total_processed": 26,
            "total_failed": 0,
        },
        "deployment": {
            "source_revision": "abc123",
            "source_event": "schedule",
            "workflow_run_id": "123456",
        },
    }


def test_validate_metadata_accepts_exact_successful_deployment() -> None:
    summary = validate_metadata(
        deployment_metadata(),
        expected_workflow_run_id="123456",
        expected_source_revision="abc123",
        expected_source_event="schedule",
        expected_sync_date=date(2026, 8, 6),
        timezone=ZoneInfo("Asia/Shanghai"),
    )

    assert summary["sync_run_id"] == "sync-run-id"
    assert summary["article_count"] == 42


def test_validate_metadata_rejects_stale_workflow_run() -> None:
    with pytest.raises(ValueError, match="workflow_run_id mismatch"):
        validate_metadata(
            deployment_metadata(),
            expected_workflow_run_id="654321",
            expected_source_revision="abc123",
            expected_source_event="schedule",
            expected_sync_date=date(2026, 8, 6),
            timezone=ZoneInfo("Asia/Shanghai"),
        )


def test_validate_metadata_rejects_partial_sync() -> None:
    payload = deployment_metadata()
    payload["sync"]["status"] = "partial_success"
    payload["sync"]["total_processed"] = 25
    payload["sync"]["total_failed"] = 1

    with pytest.raises(ValueError, match="status must be success"):
        validate_metadata(
            payload,
            expected_workflow_run_id="123456",
            expected_source_revision="abc123",
            expected_source_event="schedule",
            expected_sync_date=date(2026, 8, 6),
            timezone=ZoneInfo("Asia/Shanghai"),
        )
