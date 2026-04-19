from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.logging import setup_logging
from app.core.settings import get_settings
from app.services.scheduler import SchedulerService

settings = get_settings()
setup_logging(settings.app_debug)
scheduler_service: SchedulerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler_service
    if settings.run_scheduler:
        scheduler_service = SchedulerService(blocking=False, settings=settings)
        scheduler_service.start()
    yield
    if scheduler_service:
        scheduler_service.shutdown()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Top-journal paper tracker with RSS-first synchronization.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
