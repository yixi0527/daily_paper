from app.models.article import Article, ArticleAuthor
from app.models.journal import Journal


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_articles_endpoint_returns_seeded_article(client) -> None:
    response = client.get("/api/articles")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["items"][0]["title"] == "Circuit mechanisms of memory consolidation"


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
