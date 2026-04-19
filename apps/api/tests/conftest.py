from __future__ import annotations

from collections.abc import Generator

import pytest
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.article import Article, ArticleAuthor
from app.models.journal import Journal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = TestingSessionLocal()

    journal = Journal(
        journal_id="nature-neuroscience",
        slug="nature-neuroscience",
        journal_name="Nature Neuroscience",
        publisher="Springer Nature",
        adapter_key="nature",
        issn_print="1097-6256",
        issn_online="1546-1726",
        rss_current_issue_url="https://www.nature.com/neuro/current-issue.rss",
        rss_online_first_url="https://www.nature.com/neuro.rss",
        crossref_filters={"issn": "1546-1726"},
        homepage_url="https://www.nature.com/neuro/",
        enabled=True,
        update_priority=10,
        polling_strategy="rss_then_crossref",
        primary_source="rss",
        fallback_source="crossref",
    )
    session.add(journal)
    session.flush()

    article = Article(
        journal_id=journal.id,
        title="Circuit mechanisms of memory consolidation",
        title_slug="circuit-mechanisms-of-memory-consolidation",
        doi="10.1038/example-doi",
        url="https://www.nature.com/articles/example",
        abstract="A study about memory consolidation in cortical circuits.",
        snippet="A study about memory consolidation in cortical circuits.",
        source_category="online_first",
        article_type="Article",
        volume="29",
        issue="4",
        pages="100-120",
        article_number="NA",
        first_author="Ada Lovelace",
        authors_text="Ada Lovelace, Grace Hopper",
        source_name="nature_rss",
        source_uid="10.1038/example-doi",
        dedup_hash="hash-1",
    )
    article.authors = [
        ArticleAuthor(
            position=0, full_name="Ada Lovelace", given_name="Ada", family_name="Lovelace"
        ),
        ArticleAuthor(
            position=1, full_name="Grace Hopper", given_name="Grace", family_name="Hopper"
        ),
    ]
    session.add(article)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
