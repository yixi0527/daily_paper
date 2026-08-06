from app.services.metadata_enrichment import MetadataEnrichmentService
from app.services.types import NormalizedArticle, NormalizedAuthor


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
