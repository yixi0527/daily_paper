from datetime import UTC, datetime

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


def test_science_crossmark_history_recovers_online_date_before_the_print_issue():
    payload = {
        "title": ["Recent strengthening of eastern Pacific ENSO in the last millennium paleorecord"],
        "URL": "https://doi.org/10.1126/science.ady2660",
        "DOI": "10.1126/science.ady2660",
        "published-print": {"date-parts": [[2026, 10, 8]]},
        "assertion": [{"name": "published", "value": "2026-08-27",
                       "group": {"name": "publication_history"}}],
    }
    article = ArticleNormalizer().normalize_crossref(
        build_journal(), payload, category="doi", source_name="crossref"
    )
    assert article.online_published_at == datetime(2026, 8, 27, tzinfo=UTC)
    assert article.print_published_at == datetime(2026, 10, 8, tzinfo=UTC)
    assert article.extra_metadata["publisher_online_date"]["field"] == "crossmark.publication_history.published"

    other_journal = build_journal()
    other_journal.journal_name = "Neuron"
    other = ArticleNormalizer().normalize_crossref(
        other_journal, payload, category="doi", source_name="crossref"
    )
    assert other.online_published_at is None
