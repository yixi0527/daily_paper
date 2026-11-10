import json
from datetime import UTC, datetime
from pathlib import Path

from app.models.article import Article
from app.services.snapshot_import import import_snapshot
from app.services.static_export import StaticExportService
from app.services.web_assets import write_web_assets
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def test_snapshot_roundtrip_preserves_identity_dates_and_full_reader(db_session, tmp_path: Path):
    article = db_session.scalar(select(Article))
    article.online_published_at = datetime(2026, 11, 9, tzinfo=UTC)
    article.first_seen_at = datetime(2026, 11, 10, tzinfo=UTC)
    article.abstract = "Full abstract. " * 100
    article.abstract_zh = "完整中文摘要。" * 100
    article.title_zh = "记忆巩固的环路机制"
    db_session.commit()
    exported = StaticExportService().export(db_session, tmp_path / "export")
    bundle = json.loads((exported / "site-data.json").read_text(encoding="utf-8"))
    metadata = json.loads((exported / "metadata.json").read_text(encoding="utf-8"))
    original = bundle["articles"][0]

    engine = create_engine("sqlite://")
    from app.db.base import Base

    Base.metadata.create_all(engine)
    with Session(engine) as imported:
        assert import_snapshot(imported, bundle) == 1
        restored = imported.get(Article, original["id"])
        assert restored.doi == original["doi"]
        assert restored.online_published_at.date().isoformat() == "2026-11-09"
        assert restored.first_seen_at.date().isoformat() == "2026-11-10"
        assert [author.full_name for author in restored.authors] == ["Ada Lovelace", "Grace Hopper"]
        assert restored.abstract == original["abstract"]

    target = tmp_path / "public"
    write_web_assets(bundle, metadata, target)
    index = json.loads((target / "index.json").read_text(encoding="utf-8"))
    detail = json.loads(
        (target / "articles" / f"{original['id']}.json").read_text(encoding="utf-8")
    )
    assert detail == original
    assert len(index["articles"][0]["abstract"]) < len(detail["abstract"])
    assert index["articles"][0]["article_key"] == detail["article_key"]
    assert index["articles"][0]["online_published_at"] == detail["online_published_at"]
    assert index["dashboard"]["latest_articles"][0]["article_key"] == detail["article_key"]
    published_metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert published_metadata["translations"] == metadata["translations"]
    assert published_metadata["deployment"]["provider"] == "codex-sites"
    engine.dispose()
