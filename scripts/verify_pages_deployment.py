from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import date, datetime
from pathlib import Path
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

    return {
        "workflow_run_id": expected_workflow_run_id,
        "source_revision": expected_source_revision,
        "source_event": expected_source_event,
        "sync_run_id": sync.get("run_id"),
        "sync_finished_at": sync_finished_at.isoformat(),
        "article_count": require_integer(payload.get("article_count"), "article_count"),
        "journal_count": require_integer(payload.get("journal_count"), "journal_count"),
    }


def fetch_json(url: str, timeout: int) -> tuple[dict[str, Any], bytes]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "DailyPaperDeploymentVerifier/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Metadata request failed with HTTP {response.status}")
        content = response.read()
    payload = json.loads(content.decode("utf-8"))
    return require_object(payload, "metadata"), content


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify one exact GitHub Pages deployment")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-workflow-run-id", required=True)
    parser.add_argument("--expected-source-revision", required=True)
    parser.add_argument("--expected-source-event", required=True)
    parser.add_argument("--expected-sync-date", required=True, type=date.fromisoformat)
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.timeout < 1:
        raise ValueError("timeout must be positive")
    timezone = ZoneInfo(args.timezone)
    payload, content = fetch_json(args.url, args.timeout)
    summary = validate_metadata(
        payload,
        expected_workflow_run_id=args.expected_workflow_run_id,
        expected_source_revision=args.expected_source_revision,
        expected_source_event=args.expected_source_event,
        expected_sync_date=args.expected_sync_date,
        timezone=timezone,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
