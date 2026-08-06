from __future__ import annotations

import json
from datetime import UTC, datetime
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
from app.utils.dates import ensure_utc
from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload


def utc_isoformat(value: datetime | None) -> str | None:
    normalized = ensure_utc(value)
    return normalized.isoformat() if normalized is not None else None


class StaticExportService:
    def __init__(self) -> None:
        self.dashboard_service = DashboardService()
        self.content_policy = ContentPolicyService()
        self.article_registry = ArticleRegistryService()

    def export(
        self,
        db: Session,
        output: Path,
        *,
        source_revision: str | None = None,
        source_event: str | None = None,
        workflow_run_id: str | None = None,
    ) -> Path:
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
        latest_sync = sync_runs[0] if sync_runs else None
        sync_metadata = (
            {
                "run_id": latest_sync.id,
                "status": latest_sync.status,
                "started_at": utc_isoformat(latest_sync.started_at),
                "finished_at": utc_isoformat(latest_sync.finished_at),
                "total_journals": latest_sync.total_journals,
                "total_processed": latest_sync.total_processed,
                "total_failed": latest_sync.total_failed,
            }
            if latest_sync is not None
            else None
        )
        (output / "metadata.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_at": datetime.now(tz=UTC).isoformat(),
                    "article_count": len(payload["articles"]),
                    "journal_count": len(journals),
                    "sync": sync_metadata,
                    "deployment": {
                        "source_revision": source_revision,
                        "source_event": source_event,
                        "workflow_run_id": workflow_run_id,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return output
