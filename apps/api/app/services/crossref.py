from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.settings import Settings, get_settings
from app.services.http import HTTPClientService


class CrossrefClientService:
    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, http: HTTPClientService, settings: Settings | None = None) -> None:
        self.http = http
        self.settings = settings or get_settings()

    def fetch_recent(self, filters: dict[str, str], cursor: str | None = None) -> dict[str, Any]:
        start_date = (
            datetime.now(tz=UTC) - timedelta(days=self.settings.sync_lookback_days)
        ).date()
        filter_parts = [f"{key}:{value}" for key, value in filters.items() if value]
        filter_parts.append(f"from-pub-date:{start_date.isoformat()}")
        params = {
            "filter": ",".join(filter_parts),
            "sort": "published",
            "order": "desc",
            "rows": 100,
            "cursor": cursor or "*",
            "mailto": self.settings.crossref_mailto,
        }
        response = self.http.get(
            self.BASE_URL,
            params=params,
            headers={"Accept": "application/json"},
        )
        data = response.json()
        message = data.get("message", {})
        return {
            "items": message.get("items", []),
            "next_cursor": message.get("next-cursor"),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "request_url": str(response.url),
        }
