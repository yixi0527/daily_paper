from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
    run_id: str | None = None


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class DateRange(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
