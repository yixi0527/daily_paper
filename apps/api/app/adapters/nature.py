from __future__ import annotations

from app.adapters.base import PublisherAdapter
from app.models.journal import Journal
from app.services.types import SourceSpec


class NatureAdapter(PublisherAdapter):
    def build_sources(self, journal: Journal) -> list[SourceSpec]:
        if journal.crossref_filters:
            return [
                SourceSpec(
                    name="crossref",
                    kind="crossref",
                    metadata={"filters": journal.crossref_filters},
                )
            ]
        return []
