from __future__ import annotations

import hashlib
from datetime import datetime


class DedupService:
    @staticmethod
    def normalize_doi(doi: str | None) -> str | None:
        if not doi:
            return None
        normalized = doi.strip().lower()
        normalized = normalized.replace("https://doi.org/", "").replace("doi:", "")
        return normalized or None

    @staticmethod
    def build_fallback_hash(
        title: str, first_author: str | None, published_at: datetime | None
    ) -> str:
        material = "||".join(
            [
                (title or "").strip().lower(),
                (first_author or "").strip().lower(),
                published_at.date().isoformat() if published_at else "",
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()
