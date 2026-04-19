from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    database: str
    scheduler_enabled: bool
    latest_sync_finished_at: datetime | None
