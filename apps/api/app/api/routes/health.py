from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_db
from app.models.sync import SyncRun
from app.schemas.health import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut, summary="Health check")
def get_health(db: Session = Depends(get_db)) -> HealthOut:
    db.execute(text("SELECT 1"))
    latest_run = db.scalar(select(SyncRun).order_by(desc(SyncRun.started_at)).limit(1))
    settings = get_settings()
    return HealthOut(
        status="ok",
        database="ok",
        scheduler_enabled=settings.run_scheduler,
        latest_sync_finished_at=latest_run.finished_at if latest_run else None,
    )
