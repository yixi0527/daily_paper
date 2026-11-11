"""Fetch missing publisher Online dates; optionally apply captured publisher DOM metadata first.

Run with the project's normal PYTHONPATH and DATABASE_URL. An optional first argument
is a JSON list of {doi, url, html} observations read from publisher pages.
Request failures remain in article metadata and the supplied run log.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from app.adapters.factory import AdapterFactory
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.models.article import Article
from app.services.types import NormalizedArticle
from sqlalchemy import select
from sqlalchemy.orm import joinedload


def store_result(db, article, metadata):
    article.extra_metadata = {
        **(article.extra_metadata or {}),
        "publisher_online_date": {k: v for k, v in metadata.items() if k != "abstract"},
    }
    if metadata.get("date"):
        article.online_published_at = datetime.fromisoformat(metadata["date"])
        article.published_at = article.online_published_at
    db.commit()


def main():
    setup_logging(False)
    factory = AdapterFactory()
    counts = Counter()
    try:
        with SessionLocal() as db:
            if len(sys.argv) > 1:
                for observation in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
                    article = db.scalars(select(Article).options(joinedload(Article.journal)).where(
                        Article.doi == observation["doi"].lower()
                    )).one()
                    metadata = factory.get(article.journal).metadata_enricher.extract_publisher_metadata(observation["html"])
                    metadata.update(url=observation["url"], checked_at=datetime.now(UTC).isoformat())
                    store_result(db, article, metadata)
                    counts[metadata["status"]] += 1
            articles = db.scalars(select(Article).options(
                joinedload(Article.journal), joinedload(Article.payloads)
            ).where(Article.online_published_at.is_(None))).unique().all()
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for article in articles:
                    service = factory.get(article.journal).metadata_enricher
                    item = NormalizedArticle(
                        title=article.title, url=article.url, doi=article.doi,
                        source_category=article.source_category, source_name=article.source_name,
                        source_uid=article.source_uid, authors=[], extra_metadata=article.extra_metadata,
                        raw_payload=article.payloads[-1].payload_json if article.payloads else None,
                    )
                    futures[executor.submit(service.fetch_publisher_metadata, service.publisher_url(item))] = article
                for index, future in enumerate(as_completed(futures), 1):
                    metadata = future.result()
                    article = futures[future]
                    store_result(db, article, metadata)
                    counts[metadata["status"]] += 1
                    if index % 25 == 0 or index == len(articles):
                        print(json.dumps({"checked": index, "total": len(articles), "results": counts}), flush=True)
            print(json.dumps({"results": counts, "remaining": sum(1 for a in articles if a.online_published_at is None)}), flush=True)
    finally:
        for adapter in factory._adapters.values():
            adapter.http.close()


if __name__ == "__main__":
    main()
