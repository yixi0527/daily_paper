from __future__ import annotations

import json
from pathlib import Path

from app.api.routes.helpers import serialize_article_detail
from app.models.article import Article
from app.models.journal import Journal
from app.models.sync import SyncRun, SyncRunJournal
from app.schemas.dashboard import DashboardOut
from app.schemas.journal import JournalDetailOut
from app.schemas.sync import SyncRunOut
from app.services.article_registry import ArticleRegistryService
from app.services.content_policy import ContentPolicyService
from app.services.dashboard import DashboardService
from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload


class StaticExportService:
    def __init__(self) -> None:
        self.dashboard_service = DashboardService()
        self.content_policy = ContentPolicyService()
        self.article_registry = ArticleRegistryService()

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
                .order_by(desc(Article.first_seen_at), desc(Article.created_at))
            )
            .unique()
            .all()
        )
        visible_articles = [
            item
            for item in articles
            if self.content_policy.is_substantive_fields(
                title=item.title,
                article_type=item.article_type,
                doi=item.doi,
            )
        ]
        sync_runs = (
            db.scalars(
                select(SyncRun)
                .options(joinedload(SyncRun.journal_runs).joinedload(SyncRunJournal.journal))
                .order_by(desc(SyncRun.started_at))
                .limit(20)
            )
            .unique()
            .all()
        )

        dashboard_data = self.dashboard_service.get_dashboard(db)
        dashboard_data["latest_articles"] = [
            serialize_article_detail(item, registry=self.article_registry)
            for item in dashboard_data["latest_articles"]
        ]

        payload = {
            "journals": [
                jsonable_encoder(JournalDetailOut.model_validate(item)) for item in journals
            ],
            "articles": [
                jsonable_encoder(
                    serialize_article_detail(
                        item,
                        include_raw=True,
                        registry=self.article_registry,
                    )
                )
                for item in visible_articles
            ],
            "dashboard": jsonable_encoder(DashboardOut(**dashboard_data)),
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
                    "article_count": len(payload["articles"]),
                    "journal_count": len(journals),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return output
