from __future__ import annotations

from app.adapters.base import PublisherAdapter
from app.models.journal import Journal
from app.services.types import SourceSpec


class CrossrefOnlyAdapter(PublisherAdapter):
    def build_sources_for_category(self, journal: Journal, category: str) -> list[SourceSpec]:
        if not journal.crossref_filters:
            return []
        return [
            SourceSpec(
                name="crossref",
                kind="crossref",
                metadata={"filters": journal.crossref_filters},
            )
        ]
