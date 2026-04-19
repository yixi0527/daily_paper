from __future__ import annotations

import json
from functools import lru_cache

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def load_journal_configs() -> list[dict]:
    settings = get_settings()
    return json.loads(settings.shared_config_path.read_text(encoding="utf-8"))
