from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.article import Article, ArticleAuthor
from app.models.journal import Journal, SourceState
from app.models.sync import SyncRun, SyncRunJournal
from app.services.dedup import DedupService
from app.services.seed import SeedService
from app.utils.dates import ensure_utc
from sqlalchemy import DateTime, select
from sqlalchemy.orm import Session


def model_values(model: type, record: dict[str, Any]) -> dict[str, Any]:
    values = {}
    for column in model.__table__.columns:
        if column.name not in record:
            continue
        value = record[column.name]
        if value is not None and isinstance(column.type, DateTime):
            value = ensure_utc(datetime.fromisoformat(value))
        values[column.name] = value
    return values


def import_snapshot(db: Session, bundle: dict[str, Any]) -> int:
    if db.scalar(select(Article.id).limit(1)) is not None:
        raise ValueError("Snapshot import requires an empty article database")
    SeedService().seed_journals(db)
    journals = {journal.slug: journal for journal in db.scalars(select(Journal)).all()}
    for record in bundle["articles"]:
        acquired = ensure_utc(datetime.fromisoformat(record["acquired_at"]))
        article = Article(**model_values(Article, record))
        article.journal_id = journals[record["journal"]["slug"]].id
        article.title_slug = record["id"]
        article.first_seen_at = acquired
        article.first_author = record["first_author"]
        article.dedup_hash = DedupService.build_fallback_hash(
            article.title,
            article.first_author,
            article.published_at,
        )
        article.authors = [
            ArticleAuthor(**model_values(ArticleAuthor, author)) for author in record["authors"]
        ]
        db.add(article)
    for record in bundle["journals"]:
        journal = journals[record["slug"]]
        for state in record["source_states"]:
            journal.source_states.append(SourceState(**model_values(SourceState, state)))
    for record in bundle["sync_runs"]:
        run = SyncRun(**model_values(SyncRun, record))
        for detail in record["journal_runs"]:
            values = model_values(SyncRunJournal, detail)
            values["journal_id"] = journals[detail["journal_slug"]].id
            run.journal_runs.append(SyncRunJournal(**values))
        db.add(run)
    db.commit()
    return len(bundle["articles"])
