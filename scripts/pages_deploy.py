from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if not API_ROOT.is_dir():
    raise FileNotFoundError(API_ROOT)
sys.path.insert(0, str(API_ROOT))

from app.services.deployment_metadata import validate_site_data_integrity  # noqa: E402
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


def cache_busted_url(url: str, cache_key: str) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    query_items.append(("deployment_refresh", cache_key))
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_items),
            parts.fragment,
        )
    )


def fetch_json(
    url: str,
    *,
    timeout: int,
    cache_key: str,
) -> tuple[dict[str, Any], bytes]:
    request = urllib.request.Request(
        cache_busted_url(url, cache_key),
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "DailyPaperPagesDeploy/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Public data request failed with HTTP {response.status}: {url}")
        content = response.read()
        payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Public data must be an object: {url}")
    return payload, content


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
    site_data, source_site_data_content = fetch_json(
        args.site_data_url,
        timeout=args.timeout,
        cache_key=f"{args.workflow_run_id}-site-data",
    )
    metadata, _ = fetch_json(
        args.metadata_url,
        timeout=args.timeout,
        cache_key=f"{args.workflow_run_id}-metadata",
    )
    validate_site_data_integrity(metadata, source_site_data_content)
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
    refreshed_metadata["site_data_sha256"] = sha256(site_data_content).hexdigest()
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
