from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from typing import Iterable

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NON_SLUG_RE = re.compile(r"[^a-z0-9]+")
SCIENCE_CITATION_RE = re.compile(
    r"^(science|cell|brain|nature|neuron|the lancet neurology)\s*,?\s+",
    re.IGNORECASE,
)
ISSUE_CITATION_RE = re.compile(
    r"^(volume|issue|page|ahead of print)\b",
    re.IGNORECASE,
)
ABSTRACT_PREFIX_RE = re.compile(
    r"^(?P<prefix>"
    r"(?:[A-Z][\w&'./-]*(?:\s+[A-Z][\w&'./-]*){0,8})"
    r",\s*"
    r"(?:published\s+online|published\s+ahead\s+of\s+print|advance\s+online\s+publication|online\s+first)"
    r"\s*:\s*"
    r"[^;]+"
    r";\s*"
    r"(?:doi\s*:?\s*10\.\S+|https?://doi\.org/\S+)"
    r")\s*",
    re.IGNORECASE,
)


def strip_html(value: str | None) -> str | None:
    if not value:
        return value
    text = TAG_RE.sub(" ", value)
    text = unescape(text)
    return SPACE_RE.sub(" ", text).strip()


def compact_text(value: str | None, limit: int = 420) -> str | None:
    if not value:
        return None
    clean = sanitize_abstract_text(normalize_space(value))
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return SPACE_RE.sub(" ", value).strip()


def sanitize_abstract_text(value: str | None) -> str:
    clean = normalize_space(value)
    if not clean:
        return ""

    stripped = ABSTRACT_PREFIX_RE.sub("", clean, count=1).lstrip(" .;:-")
    return normalize_space(stripped or clean)


def slugify(value: str, limit: int = 220) -> str:
    base = NON_SLUG_RE.sub("-", value.lower()).strip("-")
    return base[:limit] or "article"


def payload_checksum(payload: object) -> str:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def looks_like_citation_text(value: str | None) -> bool:
    clean = normalize_space(strip_html(value))
    if not clean:
        return False
    lowered = clean.lower()
    if lowered.endswith(". <br />"):
        lowered = lowered.replace(". <br />", ".")
    has_citation_markers = (
        "volume" in lowered
        or re.search(r"\bvol(?:ume)?\.?\b", lowered) is not None
        or "ahead of print" in lowered
    )
    return bool(
        SCIENCE_CITATION_RE.match(clean)
        and has_citation_markers
        and len(clean.split()) <= 18
    ) or bool(ISSUE_CITATION_RE.match(clean))


def first_meaningful_text(values: Iterable[str | None]) -> str | None:
    for value in values:
        clean = sanitize_abstract_text(strip_html(value))
        if not clean or looks_like_citation_text(clean):
            continue
        return clean
    return None


def split_author_names(value: str | None) -> list[str]:
    clean = normalize_space(value)
    if not clean:
        return []

    if ";" in clean:
        parts = [item.strip() for item in clean.split(";") if item.strip()]
        return parts

    if "," not in clean:
        return [clean]

    segments = [item.strip() for item in clean.split(",") if item.strip()]
    if len(segments) <= 1:
        return [clean]

    if any(" and " in segment.lower() for segment in segments):
        pieces: list[str] = []
        for segment in segments:
            pieces.extend(
                [item.strip() for item in re.split(r"\band\b", segment, flags=re.IGNORECASE) if item.strip()]
            )
        return pieces or [clean]

    # RSS feeds from Science/Lancet often provide "A, B, C" author strings.
    if len(segments) >= 2 and all(" " in segment for segment in segments):
        return segments

    return [clean]
