from app.models.journal import Journal
from app.services.seed import SeedService
from sqlalchemy import select


def test_seed_service_loads_all_configured_journals(db_session) -> None:
    db_session.query(Journal).delete()
    db_session.commit()

    total = SeedService().seed_journals(db_session)
    count = len(db_session.scalars(select(Journal)).all())

    assert total == 14
    assert count == 14
