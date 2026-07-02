from app.models.journal import Journal
from app.services.config import load_journal_configs
from app.services.seed import SeedService
from sqlalchemy import select


def test_seed_service_loads_all_configured_journals(db_session) -> None:
    db_session.query(Journal).delete()
    db_session.commit()

    total = SeedService().seed_journals(db_session)
    journals = db_session.scalars(select(Journal)).all()
    count = len(journals)
    expected_total = len(load_journal_configs())
    slugs = {journal.slug for journal in journals}

    assert total == expected_total
    assert count == expected_total
    assert "molecular-neurodegeneration" in slugs
    assert "nature-reviews-neurology" in slugs
    assert "jama-neurology" in slugs
