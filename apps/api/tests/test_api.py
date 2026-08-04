import json
from datetime import UTC, datetime

from app.adapters.crossref_only import CrossrefOnlyAdapter
from app.models.article import Article, ArticleAuthor
from app.models.journal import Journal
from app.models.sync import SyncRun, SyncRunJournal
from app.services.article_registry import ArticleRegistryService, build_article_key, text_sha256
from app.services.static_export import StaticExportService
from app.services.sync import SyncOrchestrationService
from app.services.types import NormalizedArticle


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_sync_runs_include_journal_identity_and_failure_reason(client, db_session) -> None:
    journal = db_session.query(Journal).first()
    run = SyncRun(status="partial_success", scope="all")
    db_session.add(run)
    db_session.flush()
    db_session.add_all(
        [
            SyncRunJournal(
                sync_run_id=run.id,
                journal_id=journal.id,
                source_category="online_first",
                status="success",
                fetched_count=3,
            ),
            SyncRunJournal(
                sync_run_id=run.id,
                journal_id=journal.id,
                source_category="current_issue",
                status="failed",
                failed_count=1,
                error_message="RSS feed returned HTTP 503",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/sync/runs")

    assert response.status_code == 200
    journal_runs = response.json()[0]["journal_runs"]
    successful_run = next(item for item in journal_runs if item["status"] == "success")
    failed_run = next(item for item in journal_runs if item["status"] == "failed")
    assert successful_run["journal_slug"] == "nature-neuroscience"
    assert successful_run["journal_name"] == "Nature Neuroscience"
    assert failed_run["error_message"] == "RSS feed returned HTTP 503"


def test_sync_request_rejects_legacy_category_selection(client) -> None:
    response = client.post("/api/sync/run", json={"categories": ["online_first"]})

    assert response.status_code == 422


def test_upsert_articles_skips_records_without_a_doi(db_session) -> None:
    journal = db_session.query(Journal).first()
    article = NormalizedArticle(
        title="Record without a DOI",
        url="https://example.com/articles/no-doi",
        source_category="doi",
        source_name="crossref",
        source_uid=None,
        authors=[],
        doi=None,
    )

    counts = CrossrefOnlyAdapter().upsert_articles(db_session, journal, [article])

    assert counts == {"inserted": 0, "updated": 0}
    assert db_session.query(Article).filter_by(title="Record without a DOI").count() == 0


def test_sync_records_one_doi_indexed_result_per_journal(db_session) -> None:
    class DOIAdapter:
        def sync_journal(self, _db_session, _journal):
            return {
                "status": "success",
                "source_name": "crossref",
                "fetched": 4,
                "inserted": 3,
                "updated": 1,
                "skipped": 2,
            }

    class AdapterFactoryStub:
        def get(self, _journal):
            return DOIAdapter()

    service = SyncOrchestrationService()
    service.factory = AdapterFactoryStub()

    run = service.run(db_session, triggered_by="test")

    assert run.requested_category == "doi"
    assert run.total_journals == 1
    assert run.total_fetched == 4
    assert len(run.journal_runs) == 1
    assert run.journal_runs[0].source_category == "doi"
    assert run.journal_runs[0].skipped_count == 2


def test_articles_endpoint_returns_seeded_article(client) -> None:
    response = client.get("/api/articles")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["items"][0]["title"] == "Circuit mechanisms of memory consolidation"
    assert payload["items"][0]["article_key"] == "doi:10.1038/example-doi"
    assert payload["items"][0]["title_zh"] is None
    assert payload["items"][0]["translated_at"] is None
    assert payload["items"][0]["display_date_source"] == "acquired"


def test_search_endpoint_filters_by_author(client) -> None:
    response = client.get("/api/search", params={"author": "Ada"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert "Ada" in payload["items"][0]["article"]["authors_text"]


def test_articles_endpoint_filters_by_author(client, db_session) -> None:
    journal = db_session.query(Journal).first()
    article = Article(
        journal_id=journal.id,
        title="Adaptive planning in embodied agents",
        title_slug="adaptive-planning-in-embodied-agents",
        doi="10.1038/example-doi-2",
        url="https://www.nature.com/articles/example-2",
        abstract="A study about planning in embodied artificial agents.",
        snippet="A study about planning in embodied artificial agents.",
        source_category="online_first",
        article_type="Article",
        volume="29",
        issue="5",
        pages="121-140",
        article_number="NB",
        first_author="Alan Turing",
        authors_text="Alan Turing, Geoffrey Hinton",
        source_name="nature_rss",
        source_uid="10.1038/example-doi-2",
        dedup_hash="hash-2",
    )
    article.authors = [
        ArticleAuthor(
            position=0,
            full_name="Alan Turing",
            given_name="Alan",
            family_name="Turing",
        ),
        ArticleAuthor(
            position=1,
            full_name="Geoffrey Hinton",
            given_name="Geoffrey",
            family_name="Hinton",
        ),
    ]
    db_session.add(article)
    db_session.commit()

    response = client.get("/api/articles", params={"author": "Alan"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["items"][0]["title"] == "Adaptive planning in embodied agents"


def test_articles_endpoint_sorts_post_cutoff_articles_by_acquisition(client, db_session) -> None:
    journal = db_session.query(Journal).first()
    earlier_acquired = Article(
        journal_id=journal.id,
        title="Future metadata date",
        title_slug="future-metadata-date",
        doi="10.1038/future-metadata-date",
        url="https://doi.org/10.1038/future-metadata-date",
        abstract="Earlier acquisition.",
        snippet="Earlier acquisition.",
        source_category="online_first",
        article_type="Article",
        published_at=datetime(2026, 12, 1, tzinfo=UTC),
        first_seen_at=datetime(2026, 7, 2, tzinfo=UTC),
        source_name="crossref",
        source_uid="10.1038/future-metadata-date",
        dedup_hash="hash-future-metadata-date",
    )
    later_acquired = Article(
        journal_id=journal.id,
        title="Later acquisition",
        title_slug="later-acquisition",
        doi="10.1038/later-acquisition",
        url="https://doi.org/10.1038/later-acquisition",
        abstract="Later acquisition.",
        snippet="Later acquisition.",
        source_category="online_first",
        article_type="Article",
        published_at=datetime(2026, 7, 15, tzinfo=UTC),
        first_seen_at=datetime(2026, 7, 3, tzinfo=UTC),
        source_name="crossref",
        source_uid="10.1038/later-acquisition",
        dedup_hash="hash-later-acquisition",
    )
    db_session.add_all([earlier_acquired, later_acquired])
    db_session.commit()

    response = client.get("/api/articles")

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles.index("Later acquisition") < titles.index("Future metadata date")


def test_articles_endpoint_excludes_editorials(client, db_session) -> None:
    journal = db_session.query(Journal).first()
    article = Article(
        journal_id=journal.id,
        title="Editorial: Looking ahead",
        title_slug="editorial-looking-ahead",
        doi="10.1038/example-editorial",
        url="https://www.nature.com/articles/editorial",
        abstract="Editorial note.",
        snippet="Editorial note.",
        source_category="current_issue",
        article_type="Editorial",
        volume="29",
        issue="4",
        pages="1-2",
        article_number="ED",
        first_author="Editorial Board",
        authors_text="Editorial Board",
        source_name="nature_rss",
        source_uid="10.1038/example-editorial",
        dedup_hash="hash-editorial",
    )
    article.authors = [
        ArticleAuthor(
            position=0,
            full_name="Editorial Board",
        ),
    ]
    db_session.add(article)
    db_session.commit()

    response = client.get("/api/articles")
    assert response.status_code == 200
    payload = response.json()
    titles = [item["title"] for item in payload["items"]]
    assert "Editorial: Looking ahead" not in titles


def test_articles_endpoint_excludes_blocked_lifeline_article(client, db_session) -> None:
    journal = db_session.query(Journal).first()
    article = Article(
        journal_id=journal.id,
        title="Lifeline",
        title_slug="lifeline",
        doi="10.1016/s1474-4422(26)00210-3",
        url="https://doi.org/10.1016/s1474-4422(26)00210-3",
        abstract="A blocked non-research item.",
        snippet="A blocked non-research item.",
        source_category="online_first",
        article_type="Article",
        volume="25",
        issue="7",
        pages="1-2",
        article_number="TLN",
        first_author="The Lancet Neurology",
        authors_text="The Lancet Neurology",
        source_name="lancet_rss",
        source_uid="10.1016/s1474-4422(26)00210-3",
        dedup_hash="hash-lifeline",
    )
    article.authors = [
        ArticleAuthor(
            position=0,
            full_name="The Lancet Neurology",
        ),
    ]
    db_session.add(article)
    db_session.commit()

    list_response = client.get("/api/articles")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    list_titles = [item["title"] for item in list_payload["items"]]
    assert "Lifeline" not in list_titles

    search_response = client.get("/api/search", params={"title": "Lifeline"})
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["meta"]["total"] == 0

    detail_response = client.get(f"/api/articles/{article.id}")
    assert detail_response.status_code == 404


def test_static_export_excludes_blocked_lifeline_article(db_session, tmp_path) -> None:
    journal = db_session.query(Journal).first()
    article = Article(
        journal_id=journal.id,
        title="Lifeline",
        title_slug="lifeline",
        doi="10.1016/s1474-4422(26)00210-3",
        url="https://doi.org/10.1016/s1474-4422(26)00210-3",
        abstract="A blocked non-research item.",
        snippet="A blocked non-research item.",
        source_category="online_first",
        article_type="Article",
        source_name="lancet_rss",
        source_uid="10.1016/s1474-4422(26)00210-3",
        dedup_hash="hash-lifeline-export",
    )
    db_session.add(article)
    db_session.commit()

    StaticExportService().export(db_session, tmp_path)

    payload = json.loads((tmp_path / "site-data.json").read_text(encoding="utf-8"))
    titles = [item["title"] for item in payload["articles"]]
    assert "Lifeline" not in titles


def test_static_export_includes_translation_in_homepage_feed(db_session, tmp_path) -> None:
    article = db_session.query(Article).filter_by(doi="10.1038/example-doi").one()
    article_key = build_article_key(
        doi=article.doi,
        journal_slug=article.journal.slug,
        title=article.title,
    )
    registry_path = tmp_path / "article_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-08-02T04:00:00+00:00",
                "articles": {
                    article_key: {
                        "doi": article.doi,
                        "journal_slug": article.journal.slug,
                        "title": article.title,
                        "acquired_at": "2026-08-02T01:00:00+00:00",
                        "source_title_sha256": text_sha256(article.title),
                        "source_abstract_sha256": text_sha256(article.abstract),
                        "source_abstract": "abstract",
                        "title_zh": "记忆巩固的神经环路机制",
                        "abstract_zh": "一项关于皮层环路中记忆巩固的研究。",
                        "translation_model": "gpt-5.3-codex-spark",
                        "translated_at": "2026-08-02T04:00:00+00:00",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    export_path = tmp_path / "export"
    export_service = StaticExportService()
    export_service.article_registry = ArticleRegistryService(registry_path=registry_path)

    export_service.export(db_session, export_path)

    payload = json.loads((export_path / "site-data.json").read_text(encoding="utf-8"))
    exported_article = next(
        item for item in payload["articles"] if item["article_key"] == article_key
    )
    homepage_article = next(
        item for item in payload["dashboard"]["latest_articles"] if item["article_key"] == article_key
    )
    for item in (exported_article, homepage_article):
        assert item["title_zh"] == "记忆巩固的神经环路机制"
        assert item["abstract_zh"] == "一项关于皮层环路中记忆巩固的研究。"
        assert item["translation_model"] == "gpt-5.3-codex-spark"
