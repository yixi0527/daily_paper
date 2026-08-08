from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if not API_ROOT.is_dir():
    raise FileNotFoundError(API_ROOT)
sys.path.insert(0, str(API_ROOT))

from app.services.pages_mode import ZERO_SHA, deployment_mode  # noqa: E402

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def determine_mode(args: argparse.Namespace) -> None:
    if not SHA_RE.fullmatch(args.revision):
        raise ValueError(f"Invalid revision SHA: {args.revision}")
    changed_paths: list[str] = []
    if args.event == "push" and args.before != ZERO_SHA:
        if not SHA_RE.fullmatch(args.before):
            raise ValueError(f"Invalid before SHA: {args.before}")
        result = subprocess.run(
            ["git", "diff", "--name-only", args.before, args.revision, "--"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        changed_paths = [line for line in result.stdout.splitlines() if line]
    mode = deployment_mode(
        event_name=args.event,
        before_sha=args.before,
        changed_paths=changed_paths,
    )
    with args.github_output.open("a", encoding="utf-8") as output:
        output.write(f"mode={mode}\n")
    print(json.dumps({"mode": mode, "changed_paths": changed_paths}))


def fetch_json(url: str, *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "DailyPaperPagesDeploy/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Public data request failed with HTTP {response.status}: {url}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Public data must be an object: {url}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def refresh_translations(args: argparse.Namespace) -> None:
    if not args.registry.is_file():
        raise FileNotFoundError(args.registry)
    from app.services.static_export import (  # noqa: PLC0415
        encode_site_data,
        summarize_translations,
    )
    from app.services.static_translation_refresh import (  # noqa: PLC0415
        refresh_static_translation_payload,
    )

    timezone = ZoneInfo(args.timezone)
    now = datetime.now(tz=UTC)
    site_data = fetch_json(args.site_data_url, timeout=args.timeout)
    metadata = fetch_json(args.metadata_url, timeout=args.timeout)
    refreshed_site_data, refreshed_metadata = refresh_static_translation_payload(
        site_data,
        metadata,
        registry_path=args.registry,
        source_revision=args.source_revision,
        source_event=args.source_event,
        workflow_run_id=args.workflow_run_id,
        expected_sync_date=now.astimezone(timezone).date(),
        timezone=timezone,
        generated_at=now,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    site_data_content = encode_site_data(refreshed_site_data)
    refreshed_metadata["site_data_bytes"] = len(site_data_content)
    refreshed_metadata["translations"] = summarize_translations(
        refreshed_site_data["articles"]
    )
    (args.output / "site-data.json").write_bytes(site_data_content)
    write_json(args.output / "metadata.json", refreshed_metadata)
    print(
        json.dumps(
            {
                "mode": "translations",
                "article_count": len(refreshed_site_data["articles"]),
                "output": str(args.output),
            }
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare GitHub Pages deployment data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mode_parser = subparsers.add_parser("mode")
    mode_parser.add_argument("--event", required=True)
    mode_parser.add_argument("--before", required=True)
    mode_parser.add_argument("--revision", required=True)
    mode_parser.add_argument("--github-output", required=True, type=Path)
    mode_parser.set_defaults(handler=determine_mode)

    refresh_parser = subparsers.add_parser("refresh-translations")
    refresh_parser.add_argument("--site-data-url", required=True)
    refresh_parser.add_argument("--metadata-url", required=True)
    refresh_parser.add_argument("--registry", required=True, type=Path)
    refresh_parser.add_argument("--output", required=True, type=Path)
    refresh_parser.add_argument("--source-revision", required=True)
    refresh_parser.add_argument("--source-event", required=True)
    refresh_parser.add_argument("--workflow-run-id", required=True)
    refresh_parser.add_argument("--timezone", required=True)
    refresh_parser.add_argument("--timeout", type=int, default=120)
    refresh_parser.set_defaults(handler=refresh_translations)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
