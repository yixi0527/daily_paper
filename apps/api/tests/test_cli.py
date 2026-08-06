import pytest
from app.cli import require_complete_sync
from app.models.journal import Journal
from app.models.sync import SyncRun, SyncRunJournal
from sqlalchemy import select


def test_require_complete_sync_accepts_success() -> None:
    require_complete_sync(SyncRun(id="run-success", status="success", total_failed=0))


def test_require_complete_sync_reports_failed_journal(db_session) -> None:
    configured_journal = db_session.scalars(select(Journal)).one()
    run = SyncRun(id="run-partial", status="partial_success", total_failed=1)
    db_session.add(run)
    db_session.flush()
    db_session.add(
        SyncRunJournal(
            sync_run_id=run.id,
            journal_id=configured_journal.id,
            source_category="doi",
            status="failed",
            error_message="source returned HTTP 503",
        )
    )
    db_session.commit()

    with pytest.raises(RuntimeError, match="nature-neuroscience: source returned HTTP 503"):
        require_complete_sync(run)
