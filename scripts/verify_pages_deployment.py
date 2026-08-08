from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if not API_ROOT.is_dir():
    raise FileNotFoundError(API_ROOT)
sys.path.insert(0, str(API_ROOT))

from app.services.deployment_metadata import require_object, validate_metadata  # noqa: E402


def cache_busted_url(url: str, cache_key: str) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    query_items.append(("deployment_check", cache_key))
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_items),
            parts.fragment,
        )
    )


def fetch_json(url: str, timeout: int, cache_key: str) -> tuple[dict[str, Any], bytes]:
    request = urllib.request.Request(
        cache_busted_url(url, cache_key),
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "DailyPaperDeploymentVerifier/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Metadata request failed with HTTP {response.status}")
        content = response.read()
    payload = json.loads(content.decode("utf-8"))
    return require_object(payload, "metadata"), content


def deployment_identity(payload: dict[str, Any]) -> tuple[Any, Any, Any]:
    deployment = require_object(payload.get("deployment"), "deployment")
    return (
        deployment.get("workflow_run_id"),
        deployment.get("source_revision"),
        deployment.get("source_event"),
    )


def wait_for_expected_deployment(args: argparse.Namespace) -> tuple[dict[str, Any], bytes]:
    expected_identity = (
        args.expected_workflow_run_id,
        args.expected_source_revision,
        args.expected_source_event,
    )
    deadline = time.monotonic() + args.wait_seconds
    attempt = 0
    while True:
        cache_key = f"{args.expected_workflow_run_id}-{attempt}"
        payload, content = fetch_json(args.url, args.timeout, cache_key)
        actual_identity = deployment_identity(payload)
        if actual_identity == expected_identity:
            return payload, content
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise ValueError(
                "Deployment identity did not converge: "
                f"expected={expected_identity} actual={actual_identity} "
                f"wait_seconds={args.wait_seconds}"
            )
        time.sleep(min(args.poll_seconds, remaining_seconds))
        attempt += 1


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
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--require-complete-translations", action="store_true")
    parser.add_argument("--max-site-data-bytes", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.timeout < 1:
        raise ValueError("timeout must be positive")
    if args.wait_seconds < 0:
        raise ValueError("wait-seconds must be non-negative")
    if args.poll_seconds < 1:
        raise ValueError("poll-seconds must be positive")
    if args.max_site_data_bytes is not None and args.max_site_data_bytes < 1:
        raise ValueError("max-site-data-bytes must be positive")
    timezone = ZoneInfo(args.timezone)
    payload, content = wait_for_expected_deployment(args)
    summary = validate_metadata(
        payload,
        expected_workflow_run_id=args.expected_workflow_run_id,
        expected_source_revision=args.expected_source_revision,
        expected_source_event=args.expected_source_event,
        expected_sync_date=args.expected_sync_date,
        timezone=timezone,
        require_complete_translations=args.require_complete_translations,
        max_site_data_bytes=args.max_site_data_bytes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
