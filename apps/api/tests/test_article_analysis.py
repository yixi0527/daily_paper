from app.models.article import Article
from app.models.journal import Journal
from app.services.article_analysis import (
    ArticleAnalysisService,
    GeneratedArticleAnalysis,
    RelatedLiteratureItem,
)


class StubAnalysisClient:
    def __init__(self) -> None:
        self.related_literature: list[RelatedLiteratureItem] = []

    def generate(
        self, article: Article, related_literature: list[RelatedLiteratureItem]
    ) -> GeneratedArticleAnalysis:
        self.related_literature = related_literature
        return GeneratedArticleAnalysis(
            title_zh="记忆巩固的环路机制",
            abstract_zh="该研究关注皮层环路中的记忆巩固。",
            related_literature_notes_zh=[
                f"与库中文献 {related_literature[0].title} 共同关注记忆表征。"
            ],
            heuristic_thoughts_zh=[
                "可比较环路活动与行为巩固指标的时间耦合。",
                "可从相关文献借鉴睡眠阶段分层分析。",
                "可将细胞类型特异性干预作为后续验证方向。",
            ],
        )


def test_article_analysis_uses_library_context_and_persists_outputs(db_session) -> None:
    journal = db_session.query(Journal).first()
    related = Article(
        journal_id=journal.id,
        title="Sleep-dependent cortical plasticity in memory",
        title_slug="sleep-dependent-cortical-plasticity-in-memory",
        doi="10.1038/example-related",
        url="https://www.nature.com/articles/related",
        abstract="A study about memory representations and cortical plasticity during sleep.",
        snippet="A study about memory representations and cortical plasticity during sleep.",
        source_category="online_first",
        article_type="Article",
        source_name="nature_rss",
        source_uid="10.1038/example-related",
        dedup_hash="hash-related",
    )
    db_session.add(related)
    db_session.commit()

    article = db_session.query(Article).filter(Article.dedup_hash == "hash-1").one()
    client = StubAnalysisClient()
    analyzed = ArticleAnalysisService(client=client).analyze_article(
        db_session, article, force=True
    )

    assert client.related_literature[0].article_id == related.id
    assert analyzed.title_zh == "记忆巩固的环路机制"
    assert analyzed.abstract_zh == "该研究关注皮层环路中的记忆巩固。"
    assert analyzed.related_literature[0]["article_id"] == related.id
    assert analyzed.related_literature_notes_zh[0].startswith("与库中文献")
    assert len(analyzed.heuristic_thoughts_zh) == 3
    assert analyzed.analysis_generated_at is not None
