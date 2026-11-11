from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, document: Any) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )


def write_web_assets(
    bundle: dict[str, Any], metadata: dict[str, Any], target: Path
) -> dict[str, int]:
    target.mkdir(parents=True, exist_ok=True)
    details = target / "articles"
    details.mkdir(exist_ok=True)
    previews = []
    for article in bundle["articles"]:
        write_json(details / f"{article['id']}.json", article)
        preview = {
            key: value
            for key, value in article.items()
            if key not in {"raw_payload", "extra_metadata"}
        }
        preview["abstract"] = article["abstract"][:380] if article["abstract"] is not None else None
        preview["snippet"] = article["snippet"][:380] if article["snippet"] is not None else None
        preview["abstract_zh"] = (
            article["abstract_zh"][:220] if article["abstract_zh"] is not None else None
        )
        preview["authors"] = [
            {"position": author["position"], "full_name": author["full_name"]}
            for author in article["authors"]
        ]
        previews.append(preview)
    previews_by_id = {article["id"]: article for article in previews}
    dashboard = {
        **bundle["dashboard"],
        "latest_articles": [
            previews_by_id[article["id"]] for article in bundle["dashboard"]["latest_articles"]
        ],
    }
    index = {**bundle, "articles": previews, "dashboard": dashboard}
    write_json(target / "index.json", index)
    published_metadata = {
        key: value
        for key, value in metadata.items()
        if key not in {"site_data_sha256", "site_data_bytes", "translation_refresh"}
    }
    published_metadata["deployment"] = {"provider": "github-pages"}
    write_json(target / "metadata.json", published_metadata)
    return {"article_count": len(previews), "index_bytes": (target / "index.json").stat().st_size}
