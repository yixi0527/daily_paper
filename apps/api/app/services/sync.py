from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.factory import AdapterFactory
from app.core.logging import get_logger
from app.models.journal import Journal
from app.models.sync import SyncRun, SyncRunJournal
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

logger = get_logger(__name__)


class SyncOrchestrationService:
    def __init__(self) -> None:
        self.factory = AdapterFactory()

    def run(
        self,
        db: Session,
        *,
        journal_slug: str | None = None,
        categories: list[str] | None = None,
        triggered_by: str = "manual",
    ) -> SyncRun:
        requested_categories = categories or ["current_issue", "online_first"]
        run = SyncRun(
            triggered_by=triggered_by,
            scope=journal_slug or "all",
            requested_journal_slug=journal_slug,
            requested_category=",".join(requested_categories),
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        query = (
            select(Journal)
            .where(Journal.enabled.is_(True))
            .order_by(
                Journal.update_priority.desc(),
                Journal.journal_name.asc(),
            )
        )
        if journal_slug:
            query = query.where(Journal.slug == journal_slug)
        journals = db.scalars(query).all()
        run.total_journals = len(journals) * len(requested_categories)
        db.commit()

        for journal in journals:
            adapter = self.factory.get(journal)
            current_journal_slug = journal.slug
            for category in requested_categories:
                started_at = datetime.now(tz=UTC)
                journal_run = SyncRunJournal(
                    sync_run_id=run.id,
                    journal_id=journal.id,
                    source_category=category,
                    status="running",
                    attempts=1,
                    started_at=started_at,
                )
                db.add(journal_run)
                db.commit()
                try:
                    result = adapter.sync_category(db, journal, category)
                    journal_run.source_name = result["source_name"]
                    journal_run.status = result["status"]
                    journal_run.fetched_count = result["fetched"]
                    journal_run.inserted_count = result["inserted"]
                    journal_run.updated_count = result["updated"]
                    journal_run.finished_at = datetime.now(tz=UTC)
                    journal_run.duration_ms = int(
                        (journal_run.finished_at - started_at).total_seconds() * 1000
                    )
                    run.total_processed += 1
                    run.total_fetched += result["fetched"]
                    run.total_inserted += result["inserted"]
                    run.total_updated += result["updated"]
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    logger.exception("Journal sync failed: %s / %s", current_journal_slug, category)
                    journal_run.status = "failed"
                    journal_run.error_message = str(exc)
                    journal_run.failed_count = 1
                    journal_run.finished_at = datetime.now(tz=UTC)
                    journal_run.duration_ms = int(
                        (journal_run.finished_at - started_at).total_seconds() * 1000
                    )
                    run.total_failed += 1
                    db.commit()

        run.finished_at = datetime.now(tz=UTC)
        run.status = "success" if run.total_failed == 0 else "partial_success"
        db.commit()
        db.refresh(run)
        return run

    def recent_runs(self, db: Session, limit: int = 20) -> list[SyncRun]:
        return (
            db.scalars(
                select(SyncRun)
                .options(joinedload(SyncRun.journal_runs))
                .order_by(desc(SyncRun.started_at))
                .limit(limit)
            )
            .unique()
            .all()
        )
