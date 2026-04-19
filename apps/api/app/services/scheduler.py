from __future__ import annotations

from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from app.db.session import SessionLocal
from app.services.sync import SyncOrchestrationService
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = get_logger(__name__)


class SchedulerService:
    def __init__(self, *, blocking: bool = False, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        scheduler_cls = BlockingScheduler if blocking else BackgroundScheduler
        self.scheduler = scheduler_cls(timezone=self.settings.sync_timezone)
        self.sync_service = SyncOrchestrationService()

    def start(self) -> None:
        trigger = CronTrigger(
            hour=self.settings.sync_hour,
            minute=self.settings.sync_minute,
            timezone=self.settings.sync_timezone,
        )
        self.scheduler.add_job(
            self._run_sync_job,
            trigger=trigger,
            id="daily-sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info(
            "Scheduler started for daily sync at %02d:%02d %s",
            self.settings.sync_hour,
            self.settings.sync_minute,
            self.settings.sync_timezone,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _run_sync_job(self) -> None:
        logger.info("Running scheduled sync job")
        db = SessionLocal()
        try:
            self.sync_service.run(db, triggered_by="scheduler")
        finally:
            db.close()
