"""Gate GitHub Pages publication on the already prepared, fully translated snapshot."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(target: Path) -> dict:
    bundle = json.loads((target / "index.json").read_text(encoding="utf-8"))
    metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    pending = [
        article["article_key"]
        for article in bundle["articles"]
        if not article["title_zh"]
        or ((article["abstract"] or article["snippet"]) and not article["abstract_zh"])
    ]
    if pending or metadata["translations"]["pending_articles"]:
        raise ValueError(f"Cannot publish incomplete translations: {pending}")
    if len(bundle["articles"]) != metadata["article_count"]:
        raise ValueError("The article index and export metadata belong to different snapshots")
    return metadata


def main() -> None:
    target = ROOT / "apps/web/public/data"
    metadata = validate(target)
    if len(sys.argv) > 1 and sys.argv[1] == "stamp":
        metadata["deployment"] = {
            "provider": "github-pages",
            "source_revision": os.environ["GITHUB_SHA"],
            "source_event": os.environ["GITHUB_EVENT_NAME"],
            "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        }
        (target / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"validated_articles": metadata["article_count"], "pending_articles": 0}))


if __name__ == "__main__":
    main()
