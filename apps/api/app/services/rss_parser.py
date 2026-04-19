from __future__ import annotations

from typing import Any

import feedparser


class RSSParserService:
    def parse(self, payload: bytes) -> list[dict[str, Any]]:
        feed = feedparser.parse(payload)
        return [self._to_dict(entry) for entry in feed.entries]

    def _to_dict(self, entry: Any) -> dict[str, Any]:
        result = {}
        for key in entry.keys():
            value = entry.get(key)
            if isinstance(value, list):
                result[key] = [
                    self._to_dict(item) if hasattr(item, "keys") else item for item in value
                ]
            elif hasattr(value, "keys"):
                result[key] = self._to_dict(value)
            else:
                result[key] = value
        return result
