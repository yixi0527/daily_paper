from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG = PROJECT_ROOT / "apps" / "api" / "alembic.ini"
ALEMBIC_SCRIPTS = PROJECT_ROOT / "apps" / "api" / "alembic"


def alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_CONFIG))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
    config.attributes["database_url"] = database_url
    return config


def test_migration_graph_has_one_head() -> None:
    scripts = ScriptDirectory.from_config(alembic_config("sqlite://"))

    assert scripts.get_heads() == ["20260806_0003"]


def test_fresh_sqlite_database_upgrades_to_head(tmp_path) -> None:
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    command.upgrade(alembic_config(database_url), "head")

    engine = create_engine(database_url)
    table_names = inspect(engine).get_table_names()
    unique_constraints = inspect(engine).get_unique_constraints("articles")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()

    assert revision == "20260806_0003"
    assert "articles" in table_names
    assert "uq_articles_doi" in {item["name"] for item in unique_constraints}
    assert "uq_articles_dedup_hash" not in {item["name"] for item in unique_constraints}
