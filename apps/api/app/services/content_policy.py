from __future__ import annotations

from app.services.types import NormalizedArticle
from sqlalchemy import and_, func, not_, or_, true
from sqlalchemy.sql.elements import ColumnElement


class ContentPolicyService:
    EXCLUDED_ARTICLE_DOIS = {
        "10.1016/s1474-4422(26)00175-4",
        "10.1016/s1474-4422(26)00210-3",
    }
    EXCLUDED_EXACT_TITLES = {
        "lifeline",
    }
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
        return self.is_substantive_fields(
            title=article.title,
            article_type=article.article_type,
            doi=article.doi,
        )

    def is_substantive_fields(
        self,
        *,
        title: str | None,
        article_type: str | None,
        doi: str | None = None,
    ) -> bool:
        article_type = (article_type or "").strip().lower()
        title = (title or "").strip().lower()
        doi = self._normalize_doi(doi)

        if doi in self.EXCLUDED_ARTICLE_DOIS:
            return False
        if title in self.EXCLUDED_EXACT_TITLES:
            return False
        if article_type in self.EXCLUDED_ARTICLE_TYPES:
            return False
        if any(pattern in article_type for pattern in self.EXCLUDED_ARTICLE_TYPE_PATTERNS):
            return False
        if any(pattern in title for pattern in self.EXCLUDED_TITLE_PATTERNS):
            return False
        return True

    def article_visibility_clause(self, article_model) -> ColumnElement[bool]:
        article_type = func.lower(func.coalesce(article_model.article_type, ""))
        title = func.lower(func.trim(func.coalesce(article_model.title, "")))
        doi = func.replace(
            func.replace(func.lower(func.coalesce(article_model.doi, "")), "https://doi.org/", ""),
            "doi:",
            "",
        )

        clause = true()
        if self.EXCLUDED_ARTICLE_DOIS:
            clause = and_(clause, not_(doi.in_(sorted(self.EXCLUDED_ARTICLE_DOIS))))
        if self.EXCLUDED_EXACT_TITLES:
            clause = and_(
                clause,
                not_(title.in_(sorted(self.EXCLUDED_EXACT_TITLES))),
            )
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

    def _normalize_doi(self, doi: str | None) -> str | None:
        if not doi:
            return None
        normalized = doi.strip().lower()
        normalized = normalized.replace("https://doi.org/", "").replace("doi:", "")
        return normalized or None
