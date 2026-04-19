from __future__ import annotations

import json
from pathlib import Path

from app.models.article import Article
from app.models.journal import Journal
from app.models.sync import SyncRun
from app.schemas.article import ArticleDetailOut, AuthorOut
from app.schemas.dashboard import DashboardOut
from app.schemas.journal import JournalDetailOut
from app.schemas.sync import SyncRunOut
from app.services.dashboard import DashboardService
from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload


class StaticExportService:
    def __init__(self) -> None:
        self.dashboard_service = DashboardService()

    def export(self, db: Session, output: Path) -> Path:
        output.mkdir(parents=True, exist_ok=True)
        journals = (
            db.scalars(
                select(Journal)
                .options(joinedload(Journal.source_states))
                .order_by(Journal.update_priority.desc())
            )
            .unique()
            .all()
        )
        articles = (
            db.scalars(
                select(Article)
                .options(
                    joinedload(Article.journal),
                    joinedload(Article.authors),
                    joinedload(Article.payloads),
                )
                .order_by(desc(Article.published_at), desc(Article.created_at))
            )
            .unique()
            .all()
        )
        sync_runs = (
            db.scalars(
                select(SyncRun)
                .options(joinedload(SyncRun.journal_runs))
                .order_by(desc(SyncRun.started_at))
                .limit(20)
            )
            .unique()
            .all()
        )

        payload = {
            "journals": [
                jsonable_encoder(JournalDetailOut.model_validate(item)) for item in journals
            ],
            "articles": [
                jsonable_encoder(
                    ArticleDetailOut(
                        id=item.id,
                        title=item.title,
                        doi=item.doi,
                        url=item.url,
                        snippet=item.snippet,
                        source_category=item.source_category,
                        article_type=item.article_type,
                        volume=item.volume,
                        issue=item.issue,
                        published_at=item.published_at,
                        online_published_at=item.online_published_at,
                        print_published_at=item.print_published_at,
                        first_author=item.first_author,
                        authors_text=item.authors_text,
                        journal=JournalDetailOut.model_validate(item.journal),
                        abstract=item.abstract,
                        pages=item.pages,
                        article_number=item.article_number,
                        source_name=item.source_name,
                        source_uid=item.source_uid,
                        extra_metadata=item.extra_metadata,
                        authors=[AuthorOut.model_validate(author) for author in item.authors],
                        raw_payload=item.payloads[-1].payload_json if item.payloads else None,
                    )
                )
                for item in articles
            ],
            "dashboard": jsonable_encoder(DashboardOut(**self.dashboard_service.get_dashboard(db))),
            "sync_runs": [jsonable_encoder(SyncRunOut.model_validate(item)) for item in sync_runs],
        }

        (output / "site-data.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        (output / "metadata.json").write_text(
            json.dumps(
                {
                    "generated_at": str(
                        max((run.finished_at for run in sync_runs if run.finished_at), default=None)
                    ),
                    "article_count": len(articles),
                    "journal_count": len(journals),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return output
