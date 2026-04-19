from app.services.dedup import DedupService


def test_normalize_doi_strips_prefixes() -> None:
    assert DedupService.normalize_doi("https://doi.org/10.1038/ABC") == "10.1038/abc"
    assert (
        DedupService.normalize_doi("doi:10.1016/J.CELL.2025.01.001") == "10.1016/j.cell.2025.01.001"
    )


def test_build_fallback_hash_is_stable() -> None:
    value_a = DedupService.build_fallback_hash("A title", "Ada Lovelace", None)
    value_b = DedupService.build_fallback_hash("A title", "Ada Lovelace", None)
    assert value_a == value_b
