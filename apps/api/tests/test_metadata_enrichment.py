from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from app.models.article import Article
from app.services.content_policy import ContentPolicyService
from app.services.metadata_enrichment import MetadataEnrichmentService
from app.services.metadata_refresh import MetadataRefreshService
from app.services.types import NormalizedArticle, NormalizedAuthor
from sqlalchemy import select


@pytest.fixture()
def enricher():
    return MetadataEnrichmentService(http=None, crossref=None, normalizer=None, pubmed=None)


def article(*, abstract: str | None, authors: list[NormalizedAuthor]) -> NormalizedArticle:
    return NormalizedArticle(
        title="A test article",
        url="https://doi.org/10.1000/test",
        source_category="doi",
        source_name="crossref",
        source_uid="10.1000/test",
        authors=authors,
        doi="10.1000/test",
        abstract=abstract,
        article_type="journal-article",
    )


def test_crossref_records_are_not_fetched_again_by_doi() -> None:
    item = article(abstract=None, authors=[])

    assert MetadataEnrichmentService._needs_crossref_enrichment(
        item, source_kind="crossref"
    ) is False


def test_incomplete_rss_records_still_request_crossref_enrichment() -> None:
    item = article(abstract=None, authors=[])

    assert MetadataEnrichmentService._needs_crossref_enrichment(
        item, source_kind="rss"
    ) is True


def test_complete_rss_records_skip_crossref_enrichment() -> None:
    item = article(
        abstract="Complete abstract.",
        authors=[NormalizedAuthor(full_name="Ada Lovelace")],
    )
    item.article_type = "research-article"

    assert MetadataEnrichmentService._needs_crossref_enrichment(
        item, source_kind="rss"
    ) is False


def test_publisher_online_date_is_separate_from_issue_date(enricher):
    html = (Path(__file__).parent / "fixtures/publisher_online_date.html").read_text(encoding="utf-8")
    metadata = enricher.extract_publisher_metadata(html)
    assert metadata["date"] == "2026-10-07T00:00:00+00:00"
    assert metadata["field"] == "citation_online_date"


def test_issue_only_and_reference_dates_do_not_become_online_dates(enricher):
    metadata = enricher.extract_publisher_metadata(
        '<meta name="citation_date" content="2026/11/01">'
        '<div>References: Another paper. Published online October 7, 2026</div>'
    )
    assert metadata["status"] == "not_exposed"
    assert "date" not in metadata


def test_explicit_publisher_history_is_recognized(enricher):
    metadata = enricher.extract_publisher_metadata(
        '<div>Publication History:<br>Published online October 7, 2026</div>'
    )
    assert metadata["date"] == "2026-10-07T00:00:00+00:00"


def test_date_is_enriched_even_when_abstract_is_complete(enricher, monkeypatch):
    item = article(abstract="Complete abstract.", authors=[])
    item.published_at = datetime(2026, 11, 1, tzinfo=UTC)
    monkeypatch.setattr(enricher, "fetch_publisher_metadata", lambda url: {
        "status": "found", "date": "2026-10-07T00:00:00+00:00", "url": url,
        "field": "citation_online_date", "value": "2026/10/07",
    })
    result = enricher.enrich(None, item, source_kind="crossref")
    assert result.online_published_at == datetime(2026, 10, 7, tzinfo=UTC)
    assert result.abstract == "Complete abstract."
    assert result.extra_metadata["publisher_online_date"]["status"] == "found"


def test_publisher_denial_remains_explicit(enricher, caplog):
    enricher.http = SimpleNamespace(get=lambda url, **kwargs: httpx.Response(
        403, request=httpx.Request("GET", url), text="Forbidden",
    ))
    result = enricher.fetch_publisher_metadata("https://www.cell.com/article")
    assert result["status"] == "request_failed"
    assert "403" in result["error"]
    assert "403" in caplog.text
    assert "date" not in result


def test_publisher_html_redirect_reaches_online_metadata(enricher):
    responses = iter([
        httpx.Response(200, request=httpx.Request("GET", "https://linkinghub.elsevier.com/article"),
                       text='<meta http-equiv="refresh" content="2; url=\'/publisher?article=1&amp;view=full\'">'),
        httpx.Response(200, request=httpx.Request("GET", "https://www.cell.com/article"),
                       text='<meta name="citation_online_date" content="2026/10/07">'),
    ])
    enricher.http = SimpleNamespace(get=lambda *args, **kwargs: next(responses))
    result = enricher.fetch_publisher_metadata("https://linkinghub.elsevier.com/article")
    assert result["date"] == "2026-10-07T00:00:00+00:00"
    assert result["url"] == "https://www.cell.com/article"


def test_refresh_selects_date_only_gaps_and_persists_them(db_session, enricher, monkeypatch):
    existing = db_session.scalar(select(Article))
    original_abstract = existing.abstract
    monkeypatch.setattr(enricher, "fetch_publisher_metadata", lambda url: {
        "status": "found", "date": "2026-10-07T00:00:00+00:00", "url": url,
        "field": "citation_online_date", "value": "2026/10/07",
    })
    service = MetadataRefreshService.__new__(MetadataRefreshService)
    service.factory = SimpleNamespace(get=lambda journal: SimpleNamespace(metadata_enricher=enricher))
    service.content_policy = ContentPolicyService()
    result = service.refresh(db_session)
    assert result["updated"] == 1
    assert existing.online_published_at == datetime(2026, 10, 7, tzinfo=UTC)
    assert existing.abstract == original_abstract
    assert existing.extra_metadata["publisher_online_date"]["field"] == "citation_online_date"
