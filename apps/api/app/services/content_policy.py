from __future__ import annotations

from app.services.types import NormalizedArticle
from sqlalchemy import and_, func, not_, or_, true
from sqlalchemy.sql.elements import ColumnElement


class ContentPolicyService:
    EXCLUDED_ARTICLE_TYPES = {
        "book review",
        "books et al.",
        "books et al",
        "career feature",
        "correspondence",
        "correction",
        "corrigendum",
        "editorial",
        "editorial expression of concern",
        "erratum",
        "letter",
        "letter response",
        "memoriam",
        "obituary",
        "q&a",
        "retraction",
        "stories",
        "voices",
        "working life",
    }
    EXCLUDED_ARTICLE_TYPE_PATTERNS = (
        "book",
        "career",
        "correction",
        "corrigendum",
        "cover",
        "editorial",
        "erratum",
        "expression of concern",
        "highlight",
        "in brief",
        "meeting report",
        "news",
        "obituary",
        "podcast",
        "preview",
        "q&a",
        "retraction",
        "snapshot",
        "stories",
        "table of contents",
        "voices",
    )
    EXCLUDED_TITLE_PATTERNS = (
        "book review",
        "correction to",
        "corrigendum",
        "editorial expression of concern",
        "erratum for",
        "expression of concern",
        "in other journals",
        "news in brief",
        "obituary",
        "retraction",
        "authors' reply",
        "authors’ reply",
        "advisory board and contents",
        "peer reviewers",
        "subscription and copyright information",
        "thank you to",
        "this week in",
        "[editorial]",
    )

    def is_substantive(self, article: NormalizedArticle) -> bool:
        return self.is_substantive_fields(title=article.title, article_type=article.article_type)

    def is_substantive_fields(self, *, title: str | None, article_type: str | None) -> bool:
        article_type = (article_type or "").strip().lower()
        title = (title or "").strip().lower()

        if article_type in self.EXCLUDED_ARTICLE_TYPES:
            return False
        if any(pattern in article_type for pattern in self.EXCLUDED_ARTICLE_TYPE_PATTERNS):
            return False
        if any(pattern in title for pattern in self.EXCLUDED_TITLE_PATTERNS):
            return False
        return True

    def article_visibility_clause(self, article_model) -> ColumnElement[bool]:
        article_type = func.lower(func.coalesce(article_model.article_type, ""))
        title = func.lower(func.coalesce(article_model.title, ""))

        clause = true()
        if self.EXCLUDED_ARTICLE_TYPES:
            clause = and_(clause, not_(article_type.in_(sorted(self.EXCLUDED_ARTICLE_TYPES))))
        if self.EXCLUDED_ARTICLE_TYPE_PATTERNS:
            clause = and_(
                clause,
                not_(
                    or_(
                        *(
                            article_type.like(f"%{pattern}%")
                            for pattern in self.EXCLUDED_ARTICLE_TYPE_PATTERNS
                        )
                    )
                ),
            )
        for pattern in self.EXCLUDED_TITLE_PATTERNS:
            clause = and_(clause, not_(title.like(f"%{pattern}%")))
        return clause
