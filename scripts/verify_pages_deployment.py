from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if not API_ROOT.is_dir():
    raise FileNotFoundError(API_ROOT)
sys.path.insert(0, str(API_ROOT))

from app.services.deployment_metadata import require_object, validate_metadata  # noqa: E402


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
