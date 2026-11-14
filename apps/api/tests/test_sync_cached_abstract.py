from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.adapters.crossref_only import CrossrefOnlyAdapter
from app.models.article import Article
from app.models.journal import Journal, SourceState
from app.services.types import FetchResult, NormalizedArticle
from sqlalchemy import select


def test_sync_reuses_known_abstract_without_extra_publisher_requests(db_session, monkeypatch):
    journal = db_session.scalar(select(Journal))
    existing = db_session.scalar(select(Article))
    original_abstract = existing.abstract
    existing.online_published_at = datetime(2026, 10, 7, tzinfo=UTC)
    existing.extra_metadata = {"publisher_online_date": {"status": "found", "date": "2026-10-07T00:00:00+00:00", "url": existing.url}}
    adapter = CrossrefOnlyAdapter()
    incoming = NormalizedArticle(
        doi=existing.doi,
        title="Updated title from the current Crossref response",
        url=existing.url,
        source_category="doi",
        source_name="crossref",
        source_uid=existing.doi,
        article_type="Article",
        online_published_at=datetime(2026, 9, 22, tzinfo=UTC),
        authors=[],
    )
    result = FetchResult(
        source_name="crossref",
        source_kind="crossref",
        source_url=None,
        items=[{}],
        payload_format="json",
        status_code=200,
    )
    monkeypatch.setattr(adapter, "_fetch_by_source", lambda *args: result)
    monkeypatch.setattr(adapter, "normalize_article", lambda *args, **kwargs: incoming)

    def unexpected_request(*args, **kwargs):
        raise AssertionError("The existing abstract must avoid a redundant external request")

    monkeypatch.setattr(adapter.http, "get", unexpected_request)
    try:
        counts = adapter.sync_journal(db_session, journal)
        assert counts["updated"] == 1
        assert counts["inserted"] == 0
        assert existing.abstract == original_abstract
        assert existing.title == incoming.title
        assert existing.online_published_at == datetime(2026, 10, 7, tzinfo=UTC)
        assert existing.extra_metadata["publisher_online_date"]["status"] == "found"
    finally:
        adapter.http.close()


@pytest.mark.parametrize(
    ("incoming_date", "expected_latest"),
    [
        (datetime(2026, 10, 7, 1, tzinfo=timezone(timedelta(hours=8))), datetime(2026, 10, 7)),
        (datetime(2026, 10, 8, tzinfo=UTC), datetime(2026, 10, 8)),
    ],
)
def test_sync_compares_sqlite_publisher_dates_with_fresh_crossref_dates(
    db_session, monkeypatch, incoming_date, expected_latest
):
    journal = db_session.scalar(select(Journal))
    existing = db_session.scalar(select(Article))
    existing.online_published_at = datetime(2026, 10, 7, tzinfo=UTC)
    existing.extra_metadata = {
        "publisher_online_date": {"status": "found", "url": existing.url}
    }
    db_session.commit()
    db_session.expire_all()
    assert existing.online_published_at.tzinfo is None
    saved_doi = existing.doi
    fresh_doi = "10.1038/fresh-crossref-article"
    incoming = {
        saved_doi: NormalizedArticle(
            doi=saved_doi, title=existing.title, url=existing.url,
            source_category="doi", source_name="crossref", source_uid=saved_doi,
            authors=[], article_type="Article",
            online_published_at=datetime(2026, 9, 22, tzinfo=UTC),
        ),
        fresh_doi: NormalizedArticle(
            doi=fresh_doi, title="Fresh neuronal circuit research", url="https://example.test/new",
            abstract="A complete source abstract for the new research article.",
            source_category="doi", source_name="crossref", source_uid=fresh_doi,
            authors=[], article_type="Article", published_at=incoming_date,
            online_published_at=incoming_date,
        ),
    }
    result = FetchResult(
        source_name="crossref", source_kind="crossref", source_url="https://example.test/feed",
        items=[{"doi": doi} for doi in incoming], payload_format="json", status_code=200,
    )
    adapter = CrossrefOnlyAdapter()
    monkeypatch.setattr(adapter, "_fetch_by_source", lambda *args: result)
    monkeypatch.setattr(
        adapter, "normalize_article", lambda journal, item, **kwargs: incoming[item["doi"]]
    )

    def unexpected_request(*args, **kwargs):
        pytest.fail("Complete cached/source metadata must not request publisher pages")

    monkeypatch.setattr(adapter.http, "get", unexpected_request)
    try:
        counts = adapter.sync_journal(db_session, journal)
        db_session.expire_all()
        state = db_session.scalar(select(SourceState))
        assert counts["status"] == "success"
        assert counts["updated"] == 1
        assert counts["inserted"] == 1
        assert state.latest_seen_published_at == expected_latest
        assert state.last_error is None
        assert existing.online_published_at == datetime(2026, 10, 7)
    finally:
        adapter.http.close()

