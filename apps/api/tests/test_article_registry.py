import json
from datetime import UTC, datetime

from app.services.article_registry import (
    ArticleRegistryService,
    build_article_key,
    display_date,
    text_sha256,
)


def test_registry_resolves_persisted_translation(tmp_path) -> None:
    article_key = build_article_key(
        doi="https://doi.org/10.1038/example",
        journal_slug="nature-neuroscience",
        title="A cortical circuit study",
    )
    registry_path = tmp_path / "article_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-08-02T00:00:00+00:00",
                "articles": {
                    article_key: {
                        "acquired_at": "2026-07-20T00:00:00+00:00",
                        "source_title_sha256": text_sha256("A cortical circuit study"),
                        "source_abstract_sha256": text_sha256("Circuit-level evidence."),
                        "title_zh": "一项皮层环路研究",
                        "abstract_zh": "环路层面的证据。",
                        "translation_model": "gpt-5.3-codex-spark",
                        "translated_at": "2026-08-02T00:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    record = ArticleRegistryService(registry_path=registry_path).resolve(
        doi="10.1038/example",
        journal_slug="nature-neuroscience",
        title="A cortical circuit study",
        abstract="Circuit-level evidence.",
        snippet=None,
        first_seen_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    assert record.article_key == article_key
    assert record.title_zh == "一项皮层环路研究"
    assert record.abstract_zh == "环路层面的证据。"
    assert record.translation_model == "gpt-5.3-codex-spark"
    assert record.acquired_at == datetime(2026, 7, 20, tzinfo=UTC)


def test_registry_hides_translation_when_source_changes(tmp_path) -> None:
    title = "Original title"
    article_key = build_article_key(
        doi="10.1038/example-change",
        journal_slug="nature-neuroscience",
        title=title,
    )
    registry_path = tmp_path / "article_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-08-02T00:00:00+00:00",
                "articles": {
                    article_key: {
                        "acquired_at": "2026-07-20T00:00:00+00:00",
                        "source_title_sha256": text_sha256(title),
                        "source_abstract_sha256": text_sha256("Old abstract"),
                        "title_zh": "原标题",
                        "abstract_zh": "旧摘要",
                        "translation_model": "gpt-5.3-codex-spark",
                        "translated_at": "2026-08-02T00:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    record = ArticleRegistryService(registry_path=registry_path).resolve(
        doi="10.1038/example-change",
        journal_slug="nature-neuroscience",
        title=title,
        abstract="Revised abstract",
        snippet=None,
        first_seen_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    assert record.title_zh is None
    assert record.abstract_zh is None
    assert record.translated_at is None


def test_display_date_switches_to_acquisition_after_cutoff() -> None:
    acquired_at = datetime(2026, 7, 20, tzinfo=UTC)
    before_cutoff = datetime(2026, 6, 30, tzinfo=UTC)
    after_cutoff = datetime(2026, 7, 2, tzinfo=UTC)

    assert display_date(published_at=before_cutoff, acquired_at=acquired_at) == before_cutoff
    assert display_date(published_at=after_cutoff, acquired_at=acquired_at) == acquired_at
    assert display_date(published_at=None, acquired_at=acquired_at) == acquired_at
