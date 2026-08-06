from __future__ import annotations

import argparse
from pathlib import Path

from app.core.logging import setup_logging
from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.models.sync import SyncRun
from app.services.metadata_refresh import MetadataRefreshService
from app.services.scheduler import SchedulerService
from app.services.seed import SeedService
from app.services.static_export import StaticExportService
from app.services.sync import SyncOrchestrationService


def require_complete_sync(run: SyncRun) -> None:
    if run.status == "success":
        return
    failed_runs = [item for item in run.journal_runs if item.status == "failed"]
    for failed_run in failed_runs:
        if not failed_run.error_message:
            raise ValueError(
                f"Failed journal sync has no error message: {failed_run.journal_slug}"
            )
    failure_details = "; ".join(
        f"{item.journal_slug}: {item.error_message}" for item in failed_runs
    )
    raise RuntimeError(
        f"Sync run {run.id} finished with status={run.status}, "
        f"total_failed={run.total_failed}, failures=[{failure_details}]"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily Paper Tracker CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-journals", help="Seed or update journal configs")

    sync_parser = subparsers.add_parser("sync", help="Run synchronization")
    sync_parser.add_argument("--all", action="store_true", help="Sync all journals")
    sync_parser.add_argument("--journal", type=str, help="Sync a specific journal slug")
    sync_parser.add_argument("--triggered-by", default="cli")
    sync_parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit with an error when any requested journal fails",
    )

    export_parser = subparsers.add_parser("export-static", help="Export data for GitHub Pages")
    export_parser.add_argument("--output", type=str, default=str(get_settings().static_export_path))
    export_parser.add_argument("--source-revision")
    export_parser.add_argument("--source-event")
    export_parser.add_argument("--workflow-run-id")

    refresh_parser = subparsers.add_parser(
        "refresh-metadata", help="Reprocess stored payloads and refill missing metadata"
    )
    refresh_parser.add_argument(
        "--all",
        action="store_true",
        help="Refresh all articles instead of only records missing abstracts/snippets",
    )

    subparsers.add_parser("scheduler", help="Start the blocking scheduler")
    return parser


def main() -> None:
    settings = get_settings()
    setup_logging(settings.app_debug)
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        if args.command == "seed-journals":
            SeedService().seed_journals(db)
            print("Seeded journal configuration.")
            return
        if args.command == "sync":
            run = SyncOrchestrationService().run(
                db,
                journal_slug=args.journal,
                triggered_by=args.triggered_by,
            )
            print(f"Sync run completed: {run.id} [{run.status}]")
            if args.require_complete:
                require_complete_sync(run)
            return
        if args.command == "export-static":
            target = Path(args.output)
            StaticExportService().export(
                db,
                target,
                source_revision=args.source_revision,
                source_event=args.source_event,
                workflow_run_id=args.workflow_run_id,
            )
            print(f"Static data exported to {target}")
            return
        if args.command == "refresh-metadata":
            result = MetadataRefreshService().refresh(db, missing_only=not args.all)
            print(
                "Metadata refresh completed: "
                f"scanned={result['scanned']} updated={result['updated']} skipped={result['skipped']}"
            )
            return
        if args.command == "scheduler":
            SchedulerService(blocking=True, settings=settings).start()
            return
    finally:
        db.close()


if __name__ == "__main__":
    main()
