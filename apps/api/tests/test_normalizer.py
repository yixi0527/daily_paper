from app.models.journal import Journal
from app.services.normalizer import ArticleNormalizer


def build_journal() -> Journal:
    return Journal(
        journal_id="science",
        slug="science",
        journal_name="Science",
        publisher="AAAS",
        adapter_key="crossref_only",
        issn_print="0036-8075",
        issn_online="1095-9203",
        rss_current_issue_url="https://www.science.org/action/showFeed?type=etoc&jc=science",
        rss_online_first_url="https://www.science.org/action/showFeed?type=axatoc&jc=science",
        crossref_filters={"issn": "1095-9203"},
        homepage_url="https://www.science.org/journal/science",
        enabled=True,
        update_priority=8,
        polling_strategy="rss_then_crossref",
        primary_source="rss",
        fallback_source="crossref",
    )


def test_normalizer_uses_summary_detail_and_splits_rss_authors() -> None:
    payload = {
        "title": "A feed-based article",
        "link": "https://example.com/article",
        "summary": "Science, Vol 1, Issue 2.",
        "summary_detail": {
            "value": "<p>Detailed abstract text from summary_detail.</p>",
        },
        "author": "Alice Smith, Bob Jones, Carol Taylor",
        "dc_type": "Research Article",
        "prism_doi": "10.1000/example",
        "published": "2026-04-18T12:00:00Z",
    }

    article = ArticleNormalizer().normalize_rss(
        build_journal(),
        payload,
        category="current_issue",
        source_name="official_rss",
    )

    assert article is not None
    assert article.abstract == "Detailed abstract text from summary_detail."
    assert [author.full_name for author in article.authors] == [
        "Alice Smith",
        "Bob Jones",
        "Carol Taylor",
    ]
    assert article.article_type == "Research Article"
