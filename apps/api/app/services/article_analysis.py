from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Protocol

import httpx
from app.core.settings import Settings, get_settings
from app.models.article import Article
from app.services.content_policy import ContentPolicyService
from app.utils.text import compact_text
from pydantic import BaseModel, ConfigDict, Field
from rapidfuzz import fuzz
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session, joinedload

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")
STOPWORDS = {
    "about",
    "after",
    "among",
    "analysis",
    "based",
    "between",
    "brain",
    "cell",
    "cells",
    "data",
    "disease",
    "during",
    "effects",
    "from",
    "into",
    "model",
    "models",
    "neural",
    "paper",
    "study",
    "system",
    "that",
    "their",
    "these",
    "this",
    "through",
    "using",
    "with",
}


class RelatedLiteratureItem(BaseModel):
    article_id: str
    title: str
    journal_name: str
    published_at: str | None
    doi: str | None
    relevance_score: float
    shared_terms: list[str]
    abstract_excerpt: str | None


class GeneratedArticleAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_zh: str = Field(min_length=1)
    abstract_zh: str = Field(min_length=1)
    related_literature_notes_zh: list[str] = Field(min_length=1, max_length=5)
    heuristic_thoughts_zh: list[str] = Field(min_length=3, max_length=6)


class ArticleAnalysisClient(Protocol):
    def generate(
        self, article: Article, related_literature: list[RelatedLiteratureItem]
    ) -> GeneratedArticleAnalysis:
        ...


class OpenAICompatibleAnalysisClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(
        self, article: Article, related_literature: list[RelatedLiteratureItem]
    ) -> GeneratedArticleAnalysis:
        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY or OPENAI_API_KEY is required for article analysis")

        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.2,
            "max_tokens": 1800,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "article_translation_analysis",
                    "strict": True,
                    "schema": GeneratedArticleAnalysis.model_json_schema(),
                },
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是严谨的中文科研文献助理。只基于用户提供的文献元数据和文献库上下文输出。"
                        "翻译需要忠实、简洁；启发式思考需要明确关联文献库中的具体文献，避免编造实验细节。"
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(article, related_literature),
                },
            ],
        }
        response = httpx.post(
            f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.llm_timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return GeneratedArticleAnalysis.model_validate_json(content)

    def _build_prompt(
        self, article: Article, related_literature: list[RelatedLiteratureItem]
    ) -> str:
        source_payload = {
            "id": article.id,
            "journal": article.journal.journal_name,
            "title": article.title,
            "abstract": article.abstract,
            "snippet": article.snippet,
            "doi": article.doi,
            "article_type": article.article_type,
            "published_at": article.published_at,
        }
        related_payload = [item.model_dump() for item in related_literature]
        return (
            "请为目标文献生成中文译文和扩展思考。\n"
            "要求：\n"
            "1. title_zh 翻译标题。\n"
            "2. abstract_zh 翻译摘要；如果源元数据没有摘要，请明确写出“源元数据未提供摘要”。\n"
            "3. related_literature_notes_zh 用 1-5 条说明目标文献与文献库上下文的联系，每条点名至少一篇相关文献标题。\n"
            "4. heuristic_thoughts_zh 给出 3-6 条启发式思考，关注可迁移假设、方法借鉴、潜在验证实验或跨领域联系。\n"
            "5. 不输出 JSON 以外的文本。\n\n"
            "目标文献：\n"
            f"{json.dumps(source_payload, ensure_ascii=False, indent=2, default=str)}\n\n"
            "文献库上下文：\n"
            f"{json.dumps(related_payload, ensure_ascii=False, indent=2, default=str)}"
        )


class ArticleAnalysisService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: ArticleAnalysisClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or OpenAICompatibleAnalysisClient(self.settings)
        self.content_policy = ContentPolicyService()

    def analyze_article(self, db: Session, article: Article, *, force: bool = False) -> Article:
        if article.analysis_generated_at and not force:
            return article

        related_literature = self._related_literature(db, article)
        generated = self.client.generate(article, related_literature)

        article.title_zh = generated.title_zh.strip()
        article.abstract_zh = generated.abstract_zh.strip()
        article.related_literature = [item.model_dump() for item in related_literature]
        article.related_literature_notes_zh = [
            item.strip() for item in generated.related_literature_notes_zh
        ]
        article.heuristic_thoughts_zh = [item.strip() for item in generated.heuristic_thoughts_zh]
        article.analysis_model = self.settings.llm_model
        article.analysis_generated_at = datetime.now(UTC)
        db.add(article)
        db.commit()
        db.refresh(article)
        return article

    def analyze_missing(self, db: Session, *, limit: int, force: bool = False) -> dict[str, int]:
        query = (
            select(Article)
            .options(joinedload(Article.journal), joinedload(Article.authors))
            .where(self.content_policy.article_visibility_clause(Article))
            .order_by(desc(Article.published_at), desc(Article.created_at))
        )
        if not force:
            query = query.where(
                or_(
                    Article.title_zh.is_(None),
                    Article.abstract_zh.is_(None),
                    Article.heuristic_thoughts_zh.is_(None),
                )
            )

        articles = db.scalars(query.limit(limit)).unique().all()
        for article in articles:
            self.analyze_article(db, article, force=True)
        return {"scanned": len(articles), "updated": len(articles)}

    def _related_literature(self, db: Session, article: Article) -> list[RelatedLiteratureItem]:
        candidates = (
            db.scalars(
                select(Article)
                .options(joinedload(Article.journal))
                .where(Article.id != article.id)
                .where(self.content_policy.article_visibility_clause(Article))
                .order_by(desc(Article.published_at), desc(Article.created_at))
                .limit(self.settings.analysis_candidate_limit)
            )
            .unique()
            .all()
        )
        if not candidates:
            raise ValueError("At least one library article is required for linked analysis")

        target_tokens = self._tokens(article)
        target_text = self._article_text(article)
        scored = [
            (self._score_related(article, target_text, target_tokens, candidate), candidate)
            for candidate in candidates
        ]
        scored.sort(key=lambda item: item[0]["relevance_score"], reverse=True)
        return [
            RelatedLiteratureItem(
                article_id=candidate.id,
                title=candidate.title,
                journal_name=candidate.journal.journal_name,
                published_at=candidate.published_at.isoformat()
                if candidate.published_at
                else None,
                doi=candidate.doi,
                relevance_score=score["relevance_score"],
                shared_terms=score["shared_terms"],
                abstract_excerpt=compact_text(candidate.abstract or candidate.snippet, limit=700),
            )
            for score, candidate in scored[: self.settings.analysis_context_limit]
        ]

    def _score_related(
        self,
        target: Article,
        target_text: str,
        target_tokens: set[str],
        candidate: Article,
    ) -> dict[str, object]:
        candidate_tokens = self._tokens(candidate)
        shared_terms = sorted(target_tokens & candidate_tokens)[:10]
        token_score = len(shared_terms) / max(len(target_tokens), 1)
        title_score = fuzz.token_set_ratio(target.title, candidate.title) / 100
        candidate_text = self._article_text(candidate)
        abstract_score = fuzz.partial_ratio(target_text, candidate_text) / 100
        relevance_score = round((token_score * 0.55) + (title_score * 0.3) + (abstract_score * 0.15), 4)
        return {
            "relevance_score": relevance_score,
            "shared_terms": shared_terms,
        }

    def _tokens(self, article: Article) -> set[str]:
        return {
            match.group(0).lower()
            for match in TOKEN_RE.finditer(self._article_text(article))
            if match.group(0).lower() not in STOPWORDS and len(match.group(0)) >= 4
        }

    def _article_text(self, article: Article) -> str:
        return " ".join(
            item
            for item in [
                article.title,
                article.abstract,
                article.snippet,
                article.title_zh,
                article.abstract_zh,
            ]
            if item
        )
