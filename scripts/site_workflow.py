from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.cli import require_complete_sync
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.services.seed import SeedService
from app.services.snapshot_import import import_snapshot
from app.services.static_export import StaticExportService, summarize_translations
from app.services.sync import SyncOrchestrationService
from app.services.web_assets import write_web_assets
from article_registry import merge, prepare, verify
from run_nvidia_translation import (
    DEFAULT_API_URL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    exclusive_lock,
    translate_batches,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("DAILY_PAPER_RUNTIME_DIR", ROOT / "data" / "site-workflow"))
REGISTRY = ROOT / "packages" / "shared" / "data" / "article_registry.json"


def initialize() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "scripts/run_alembic.py"), "upgrade", "head"],
        cwd=ROOT,
        check=True,
    )


def bootstrap(snapshot: Path) -> None:
    initialize()
    bundle = json.loads(snapshot.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        count = import_snapshot(db, bundle)
    print(json.dumps({"imported_articles": count}), flush=True)


def update() -> None:
    initialize()
    state_path = RUNTIME / "state.json"
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    with exclusive_lock(RUNTIME / ".update.lock"):
        previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        if previous.get("date") == today and previous.get("status") in {"ready", "published"}:
            print(json.dumps(previous, ensure_ascii=False), flush=True)
            return
        run_id = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        run_dir = RUNTIME / "runs" / run_id
        run_dir.mkdir(parents=True)
        state = {
            "run_id": run_id,
            "date": today,
            "status": "running",
            "stage": "sync",
            "last_sync_date": previous.get("last_sync_date"),
            "started_at": datetime.now(UTC).isoformat(),
            "checkout_path": str(ROOT),
        }
        write_json(state_path, state)
        try:
            setup_logging(False)
            with SessionLocal() as db:
                SeedService().seed_journals(db)
                if state["last_sync_date"] != today:
                    run = SyncOrchestrationService().run(db, triggered_by="codex-sites")
                    require_complete_sync(run)
                    state["last_sync_date"] = today
                state["stage"] = "translation"
                write_json(state_path, state)
                staging = run_dir / "export"
                StaticExportService().export(db, staging, source_event="codex-sites")
                batches = run_dir / "batches"
                prepare(
                    SimpleNamespace(
                        site_data=staging / "site-data.json",
                        registry=REGISTRY,
                        work_dir=batches,
                        model=DEFAULT_MODEL,
                        batch_size=1,
                        max_source_chars=12000,
                        default_acquired_at=None,
                    )
                )
                manifest = json.loads((batches / "manifest.json").read_text(encoding="utf-8"))
                state["translation_count"] = manifest["pending_count"]
                write_json(state_path, state)
                if manifest["pending_count"]:
                    translate_batches(
                        batch_paths=[batches / name for name in manifest["batch_files"]],
                        cache_path=RUNTIME / "nvidia-cache.json",
                        api_url=DEFAULT_API_URL,
                        api_key=os.environ["NVIDIA_API_KEY"],
                        model=DEFAULT_MODEL,
                        timeout=300,
                        max_tokens=DEFAULT_MAX_TOKENS,
                        workers=4,
                        resume=True,
                    )
                    merge(
                        SimpleNamespace(
                            registry=REGISTRY,
                            manifest=batches / "manifest.json",
                            model=DEFAULT_MODEL,
                            translated_at=None,
                        )
                    )
                verify(
                    SimpleNamespace(
                        site_data=staging / "site-data.json", registry=REGISTRY, model=None
                    )
                )
                StaticExportService().export(db, staging, source_event="codex-sites")
            bundle = json.loads((staging / "site-data.json").read_text(encoding="utf-8"))
            counts = summarize_translations(bundle["articles"])
            if counts["pending_articles"]:
                raise ValueError(f"Translations remain incomplete: {counts}")
            metadata = json.loads((staging / "metadata.json").read_text(encoding="utf-8"))
            state.update(write_web_assets(bundle, metadata, ROOT / "apps/web/public/data"))
            state.update(status="ready", stage="publish", finished_at=datetime.now(UTC).isoformat())
            write_json(state_path, state)
            print(json.dumps(state, ensure_ascii=False), flush=True)
        finally:
            error = sys.exception()
            if error is not None:
                state.update(status="failed", error="".join(traceback.format_exception(error)))
                write_json(state_path, state)


def refresh_assets() -> None:
    state = json.loads((RUNTIME / "state.json").read_text(encoding="utf-8"))
    if state["status"] not in {"ready", "published"}:
        raise ValueError("The library update must finish before assets are prepared")
    export = RUNTIME / "runs" / state["run_id"] / "export"
    bundle = json.loads((export / "site-data.json").read_text(encoding="utf-8"))
    metadata = json.loads((export / "metadata.json").read_text(encoding="utf-8"))
    result = write_web_assets(bundle, metadata, ROOT / "apps/web/public/data")
    state.update(result, checkout_path=str(ROOT))
    write_json(RUNTIME / "state.json", state)
    print(json.dumps(result), flush=True)


def record_publication() -> None:
    receipt = json.load(sys.stdin)
    state = json.loads((RUNTIME / "state.json").read_text(encoding="utf-8"))
    receipt["run_id"] = state["run_id"]
    write_json(RUNTIME / "publication.json", receipt)
    if receipt["published"]:
        subprocess.run(
            [
                r"C:\Program Files\Git\cmd\git.exe",
                "update-ref",
                "refs/heads/codex/site-live",
                receipt["commit_sha"],
            ],
            cwd=ROOT,
            check=True,
        )
        state.update(
            status="published",
            published_at=datetime.now(UTC).isoformat(),
            published_url=receipt["url"],
        )
        write_json(RUNTIME / "state.json", state)
    print(json.dumps({"publication_recorded": True, "published": receipt["published"]}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        bootstrap(Path(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "assets":
        refresh_assets()
    elif len(sys.argv) > 1 and sys.argv[1] == "publication":
        record_publication()
    else:
        update()
