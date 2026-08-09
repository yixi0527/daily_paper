from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def require_positive_integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def parse_run_list(content: str) -> dict[str, Any]:
    if not content:
        raise ValueError("GitHub CLI returned no schedule-run JSON")
    payload = json.loads(content)
    if not isinstance(payload, list):
        raise ValueError("GitHub schedule-run result must be a list")
    if len(payload) != 1:
        raise ValueError(f"Expected one latest schedule run, found {len(payload)}")
    return require_object(payload[0], "schedule run")


def validate_schedule_run(
    run: dict[str, Any],
    *,
    timezone: ZoneInfo,
    expected_date: date,
) -> dict[str, Any]:
    database_id = require_positive_integer(run.get("databaseId"), "databaseId")
    status = require_string(run.get("status"), "status")
    if status != "completed":
        raise ValueError(f"Latest schedule run status must be completed: {status}")

    conclusion = require_string(run.get("conclusion"), "conclusion")
    if conclusion != "success":
        raise ValueError(f"Latest schedule run conclusion must be success: {conclusion}")

    event = require_string(run.get("event"), "event")
    if event != "schedule":
        raise ValueError(f"Latest schedule run event must be schedule: {event}")

    created_at_text = require_string(run.get("createdAt"), "createdAt")
    head_sha = require_string(run.get("headSha"), "headSha")
    url = require_string(run.get("url"), "url")

    if SHA_RE.fullmatch(head_sha) is None:
        raise ValueError(f"headSha must be a lowercase 40-character Git SHA: {head_sha}")
    if not url.startswith("https://github.com/"):
        raise ValueError(f"url must be a GitHub HTTPS URL: {url}")

    created_at = datetime.fromisoformat(created_at_text)
    if created_at.tzinfo is None:
        raise ValueError("createdAt must include a timezone offset")
    created_at_local = created_at.astimezone(timezone)
    actual_date = created_at_local.date()
    if actual_date != expected_date:
        raise ValueError(
            "Latest schedule run is outside the expected local date: "
            f"expected={expected_date.isoformat()} actual={actual_date.isoformat()} "
            f"created_at={created_at_text} created_at_local={created_at_local.isoformat()}"
        )

    return {
        "database_id": str(database_id),
        "status": status,
        "conclusion": conclusion,
        "event": event,
        "created_at": created_at_text,
        "created_at_local": created_at_local.isoformat(),
        "local_date": actual_date.isoformat(),
        "head_sha": head_sha,
        "url": url,
        "timezone": timezone.key,
    }


def query_latest_schedule_run(
    *,
    gh_executable: Path,
    repository: str,
    workflow: str,
    branch: str,
) -> dict[str, Any]:
    arguments = [
        str(gh_executable),
        "run",
        "list",
        "--repo",
        repository,
        "--workflow",
        workflow,
        "--branch",
        branch,
        "--event",
        "schedule",
        "--json",
        "databaseId,status,conclusion,event,createdAt,headSha,url",
        "--limit",
        "1",
    ]
    result = subprocess.run(
        arguments,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return parse_run_list(result.stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the latest daily Pages schedule run in one IANA timezone"
    )
    parser.add_argument("--gh-executable", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--timezone", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.gh_executable.is_file():
        raise FileNotFoundError(args.gh_executable)
    if REPOSITORY_RE.fullmatch(args.repository) is None:
        raise ValueError(f"Invalid GitHub repository: {args.repository}")
    timezone = ZoneInfo(args.timezone)
    expected_date = datetime.now(timezone).date()
    run = query_latest_schedule_run(
        gh_executable=args.gh_executable,
        repository=args.repository,
        workflow=args.workflow,
        branch=args.branch,
    )
    summary = validate_schedule_run(
        run,
        timezone=timezone,
        expected_date=expected_date,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
