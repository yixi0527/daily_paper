from __future__ import annotations

from app.adapters.cell_press import CellPressAdapter
from app.adapters.crossref_only import CrossrefOnlyAdapter
from app.adapters.nature import NatureAdapter
from app.adapters.springer import SpringerRSSAdapter
from app.models.journal import Journal


class AdapterFactory:
    def __init__(self) -> None:
        self._adapters = {
            "cell_press": CellPressAdapter(),
            "nature": NatureAdapter(),
            "springer_rss": SpringerRSSAdapter(),
            "crossref_only": CrossrefOnlyAdapter(),
        }

    def get(self, journal: Journal):
        if journal.adapter_key not in self._adapters:
            raise KeyError(f"Unknown adapter: {journal.adapter_key}")
        return self._adapters[journal.adapter_key]
