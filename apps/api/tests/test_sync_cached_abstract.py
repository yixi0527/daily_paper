from app.adapters.crossref_only import CrossrefOnlyAdapter
from app.models.article import Article
from app.models.journal import Journal
from app.services.types import FetchResult, NormalizedArticle
from sqlalchemy import select


def test_sync_reuses_known_abstract_without_extra_publisher_requests(db_session, monkeypatch):
    journal = db_session.scalar(select(Journal))
    existing = db_session.scalar(select(Article))
    original_abstract = existing.abstract
    adapter = CrossrefOnlyAdapter()
    incoming = NormalizedArticle(
        doi=existing.doi,
        title="Updated title from the current Crossref response",
        url=existing.url,
        source_category="doi",
        source_name="crossref",
        source_uid=existing.doi,
        article_type="Article",
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
    finally:
        adapter.http.close()
