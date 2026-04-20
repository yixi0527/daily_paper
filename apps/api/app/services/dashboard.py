from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.article import Article
from app.models.journal import Journal
from app.models.sync import SyncRun
from app.services.content_policy import ContentPolicyService
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload


class DashboardService:
    def __init__(self) -> None:
        self.content_policy = ContentPolicyService()

    def get_dashboard(self, db: Session) -> dict:
        today = datetime.now(tz=UTC).date()
        today_count = (
            db.scalar(
                select(func.count())
                .select_from(Article)
                .where(self.content_policy.article_visibility_clause(Article))
                .where(func.date(Article.created_at) == today)
            )
            or 0
        )
        trend = []
        for offset in range(6, -1, -1):
            point_date = today - timedelta(days=offset)
            count = (
                db.scalar(
                    select(func.count())
                    .select_from(Article)
                    .where(self.content_policy.article_visibility_clause(Article))
                    .where(func.date(Article.created_at) == point_date)
                )
                or 0
            )
            trend.append({"date": point_date.isoformat(), "count": count})
        journal_rows = db.execute(
            select(Journal.slug, Journal.journal_name, func.count(Article.id))
            .join(Article, Article.journal_id == Journal.id)
            .where(self.content_policy.article_visibility_clause(Article))
            .group_by(Journal.slug, Journal.journal_name)
            .order_by(desc(func.count(Article.id)))
        ).all()
        latest_articles = (
            db.scalars(
                select(Article)
                .options(joinedload(Article.journal), joinedload(Article.authors))
                .where(self.content_policy.article_visibility_clause(Article))
                .where(or_(Article.abstract.is_not(None), Article.snippet.is_not(None)))
                .order_by(desc(Article.published_at), desc(Article.created_at))
                .limit(20)
            )
            .unique()
            .all()
        )
        last_sync = db.scalar(select(SyncRun).order_by(desc(SyncRun.started_at)).limit(1))
        return {
            "today_new_articles": today_count,
            "last_sync_status": last_sync.status if last_sync else None,
            "trend": trend,
            "by_journal": [
                {"journal_slug": slug, "journal_name": name, "count": count}
                for slug, name, count in journal_rows
            ],
            "latest_articles": latest_articles,
        }
