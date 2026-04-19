from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.sync import SyncRunOut, SyncRunRequest
from app.services.sync import SyncOrchestrationService

router = APIRouter()
service = SyncOrchestrationService()


@router.post("/run", response_model=SyncRunOut, summary="Run sync for all journals")
def run_sync(payload: SyncRunRequest, db: Session = Depends(get_db)) -> SyncRunOut:
    run = service.run(db, categories=payload.categories, triggered_by=payload.triggered_by)
    return SyncRunOut.model_validate(run)


@router.post(
    "/run/{journal_slug}", response_model=SyncRunOut, summary="Run sync for a single journal"
)
def run_single_journal_sync(
    journal_slug: str,
    payload: SyncRunRequest,
    db: Session = Depends(get_db),
) -> SyncRunOut:
    run = service.run(
        db,
        journal_slug=journal_slug,
        categories=payload.categories,
        triggered_by=payload.triggered_by,
    )
    return SyncRunOut.model_validate(run)


@router.get("/runs", response_model=list[SyncRunOut], summary="List recent sync runs")
def list_sync_runs(db: Session = Depends(get_db)) -> list[SyncRunOut]:
    runs = service.recent_runs(db)
    return [SyncRunOut.model_validate(run) for run in runs]
