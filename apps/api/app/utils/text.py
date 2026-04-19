from __future__ import annotations

import hashlib
import json
import re
from html import unescape

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


def strip_html(value: str | None) -> str | None:
    if not value:
        return value
    text = TAG_RE.sub(" ", value)
    text = unescape(text)
    return SPACE_RE.sub(" ", text).strip()


def compact_text(value: str | None, limit: int = 420) -> str | None:
    if not value:
        return None
    clean = SPACE_RE.sub(" ", value).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def slugify(value: str, limit: int = 220) -> str:
    base = NON_SLUG_RE.sub("-", value.lower()).strip("-")
    return base[:limit] or "article"


def payload_checksum(payload: object) -> str:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
