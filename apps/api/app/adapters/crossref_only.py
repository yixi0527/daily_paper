from __future__ import annotations

from app.adapters.base import PublisherAdapter
from app.models.journal import Journal
from app.services.types import SourceSpec


class CrossrefOnlyAdapter(PublisherAdapter):
    def build_sources_for_category(self, journal: Journal, category: str) -> list[SourceSpec]:
        sources: list[SourceSpec] = []
        if category == "current_issue" and journal.rss_current_issue_url:
            sources.append(SourceSpec(name="official_rss", kind="rss", url=journal.rss_current_issue_url))
        if category == "online_first" and journal.rss_online_first_url:
            sources.append(SourceSpec(name="official_rss", kind="rss", url=journal.rss_online_first_url))
        if journal.crossref_filters:
            sources.append(
                SourceSpec(
                    name="crossref",
                    kind="crossref",
                    metadata={"filters": journal.crossref_filters},
                )
            )
        return sources
