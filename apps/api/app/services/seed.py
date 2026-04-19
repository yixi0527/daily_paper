from __future__ import annotations

from app.models.journal import Journal
from app.services.config import load_journal_configs
from sqlalchemy import select
from sqlalchemy.orm import Session


class SeedService:
    def seed_journals(self, db: Session) -> int:
        configs = load_journal_configs()
        count = 0
        for config in configs:
            journal = db.scalar(select(Journal).where(Journal.slug == config["slug"]))
            if journal is None:
                journal = Journal(**config)
                db.add(journal)
                count += 1
            else:
                for key, value in config.items():
                    setattr(journal, key, value)
        db.commit()
        return len(configs)
