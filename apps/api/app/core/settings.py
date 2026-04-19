from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Daily Paper Tracker", alias="APP_NAME")
    app_env: Literal["development", "test", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    web_base_url: str = Field(default="http://localhost:5173", alias="WEB_BASE_URL")
    frontend_cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:4173",
        alias="FRONTEND_CORS_ORIGINS",
    )
    database_url: str = Field(
        default="sqlite:///./data/daily_paper.db",
        alias="DATABASE_URL",
    )
    sync_timezone: str = Field(default="Asia/Shanghai", alias="SYNC_TIMEZONE")
    sync_hour: int = Field(default=22, alias="SYNC_HOUR")
    sync_minute: int = Field(default=0, alias="SYNC_MINUTE")
    sync_lookback_days: int = Field(default=60, alias="SYNC_LOOKBACK_DAYS")
    sync_max_pages: int = Field(default=5, alias="SYNC_MAX_PAGES")
    sync_http_timeout: int = Field(default=30, alias="SYNC_HTTP_TIMEOUT")
    sync_retry_attempts: int = Field(default=4, alias="SYNC_RETRY_ATTEMPTS")
    sync_min_interval_seconds: float = Field(default=1.5, alias="SYNC_MIN_INTERVAL_SECONDS")
    http_user_agent: str = Field(
        default="DailyPaperTracker/1.0 (+https://github.com/your-org/daily_paper)",
        alias="HTTP_USER_AGENT",
    )
    crossref_mailto: str = Field(default="research@example.com", alias="CROSSREF_MAILTO")
    run_scheduler: bool = Field(default=False, alias="RUN_SCHEDULER")
    export_static_data_dir: str = Field(
        default="apps/web/public/data",
        alias="EXPORT_STATIC_DATA_DIR",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip() for origin in self.frontend_cors_origins.split(",") if origin.strip()
        ]

    @property
    def shared_config_path(self) -> Path:
        return ROOT_DIR / "packages" / "shared" / "config" / "journals.json"

    @property
    def static_export_path(self) -> Path:
        return ROOT_DIR / self.export_static_data_dir


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
