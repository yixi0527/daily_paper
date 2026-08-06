from __future__ import annotations

from typing import Literal

REGISTRY_PATH = "packages/shared/data/article_registry.json"
ZERO_SHA = "0" * 40


def deployment_mode(
    *,
    event_name: str,
    before_sha: str,
    changed_paths: list[str],
) -> Literal["full", "translations"]:
    if event_name not in {"push", "schedule", "workflow_dispatch"}:
        raise ValueError(f"Unsupported GitHub event: {event_name}")
    if event_name != "push" or before_sha == ZERO_SHA:
        return "full"
    if not changed_paths:
        raise ValueError("Push event contains no changed paths")
    return "translations" if set(changed_paths) == {REGISTRY_PATH} else "full"
