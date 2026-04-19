from __future__ import annotations

import argparse
from pathlib import Path

from app.core.logging import setup_logging
from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.services.scheduler import SchedulerService
from app.services.seed import SeedService
from app.services.static_export import StaticExportService
from app.services.sync import SyncOrchestrationService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily Paper Tracker CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-journals", help="Seed or update journal configs")

    sync_parser = subparsers.add_parser("sync", help="Run synchronization")
    sync_parser.add_argument("--all", action="store_true", help="Sync all journals")
    sync_parser.add_argument("--journal", type=str, help="Sync a specific journal slug")
    sync_parser.add_argument(
        "--category",
        choices=["current_issue", "online_first"],
        action="append",
        help="Limit sync to one or more categories",
    )
    sync_parser.add_argument("--triggered-by", default="cli")

    export_parser = subparsers.add_parser("export-static", help="Export data for GitHub Pages")
    export_parser.add_argument("--output", type=str, default=str(get_settings().static_export_path))

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
                categories=args.category,
                triggered_by=args.triggered_by,
            )
            print(f"Sync run completed: {run.id} [{run.status}]")
            return
        if args.command == "export-static":
            target = Path(args.output)
            StaticExportService().export(db, target)
            print(f"Static data exported to {target}")
            return
        if args.command == "scheduler":
            SchedulerService(blocking=True, settings=settings).start()
            return
    finally:
        db.close()


if __name__ == "__main__":
    main()
