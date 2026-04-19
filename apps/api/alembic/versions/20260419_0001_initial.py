"""initial schema"""

import sqlalchemy as sa
from alembic import op

revision = "20260419_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("journal_id", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("journal_name", sa.String(length=255), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=False),
        sa.Column("adapter_key", sa.String(length=100), nullable=False),
        sa.Column("issn_print", sa.String(length=32), nullable=True),
        sa.Column("issn_online", sa.String(length=32), nullable=True),
        sa.Column("rss_current_issue_url", sa.Text(), nullable=True),
        sa.Column("rss_online_first_url", sa.Text(), nullable=True),
        sa.Column("crossref_filters", sa.JSON(), nullable=True),
        sa.Column("homepage_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("update_priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("polling_strategy", sa.String(length=100), nullable=False),
        sa.Column("primary_source", sa.String(length=100), nullable=True),
        sa.Column("fallback_source", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("journal_id", name="uq_journals_journal_id"),
        sa.UniqueConstraint("slug", name="uq_journals_slug"),
    )
    op.create_index("ix_journals_journal_id", "journals", ["journal_id"])
    op.create_index("ix_journals_slug", "journals", ["slug"])
    op.create_index("ix_journals_journal_name", "journals", ["journal_name"])
    op.create_index("ix_journals_publisher", "journals", ["publisher"])

    op.create_table(
        "source_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "journal_id",
            sa.Integer(),
            sa.ForeignKey("journals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_category", sa.String(length=50), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("etag", sa.String(length=512), nullable=True),
        sa.Column("last_modified", sa.String(length=512), nullable=True),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_seen_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "journal_id",
            "source_category",
            "source_name",
            name="uq_source_states_journal_category_name",
        ),
    )
    op.create_index("ix_source_states_journal_id", "source_states", ["journal_id"])
    op.create_index("ix_source_states_source_category", "source_states", ["source_category"])
    op.create_index("ix_source_states_source_name", "source_states", ["source_name"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("triggered_by", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("requested_journal_slug", sa.String(length=120), nullable=True),
        sa.Column("requested_category", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_journals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sync_runs_started_at", "sync_runs", ["started_at"])

    op.create_table(
        "articles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "journal_id",
            sa.Integer(),
            sa.ForeignKey("journals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("title_slug", sa.String(length=255), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("source_category", sa.String(length=50), nullable=False),
        sa.Column("article_type", sa.String(length=100), nullable=True),
        sa.Column("volume", sa.String(length=50), nullable=True),
        sa.Column("issue", sa.String(length=50), nullable=True),
        sa.Column("pages", sa.String(length=100), nullable=True),
        sa.Column("article_number", sa.String(length=100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("online_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("print_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_author", sa.String(length=255), nullable=True),
        sa.Column("authors_text", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_uid", sa.String(length=512), nullable=True),
        sa.Column("dedup_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload_checksum", sa.String(length=64), nullable=True),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("doi", name="uq_articles_doi"),
        sa.UniqueConstraint("dedup_hash", name="uq_articles_dedup_hash"),
    )
    op.create_index("ix_articles_journal_id", "articles", ["journal_id"])
    op.create_index("ix_articles_title", "articles", ["title"])
    op.create_index("ix_articles_title_slug", "articles", ["title_slug"])
    op.create_index("ix_articles_doi", "articles", ["doi"])
    op.create_index("ix_articles_source_category", "articles", ["source_category"])
    op.create_index("ix_articles_article_type", "articles", ["article_type"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_first_author", "articles", ["first_author"])
    op.create_index("ix_articles_source_name", "articles", ["source_name"])
    op.create_index("ix_articles_dedup_hash", "articles", ["dedup_hash"])
    op.create_index("ix_articles_journal_published", "articles", ["journal_id", "published_at"])

    op.create_table(
        "article_authors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "article_id",
            sa.String(length=36),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("given_name", sa.String(length=255), nullable=True),
        sa.Column("family_name", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("affiliation", sa.Text(), nullable=True),
        sa.UniqueConstraint("article_id", "position", name="uq_article_authors_article_position"),
    )
    op.create_index("ix_article_authors_article_id", "article_authors", ["article_id"])
    op.create_index("ix_article_authors_full_name", "article_authors", ["full_name"])

    op.create_table(
        "article_payloads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "article_id",
            sa.String(length=36),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "journal_id",
            sa.Integer(),
            sa.ForeignKey("journals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_category", sa.String(length=50), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("payload_format", sa.String(length=50), nullable=False),
        sa.Column("payload_text", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("payload_checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_article_payloads_article_id", "article_payloads", ["article_id"])
    op.create_index("ix_article_payloads_journal_id", "article_payloads", ["journal_id"])
    op.create_index("ix_article_payloads_source_category", "article_payloads", ["source_category"])
    op.create_index("ix_article_payloads_source_name", "article_payloads", ["source_name"])
    op.create_index("ix_article_payloads_checksum", "article_payloads", ["payload_checksum"])
    op.create_index(
        "ix_article_payloads_article_id_fetched", "article_payloads", ["article_id", "fetched_at"]
    )

    op.create_table(
        "sync_run_journals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "sync_run_id",
            sa.String(length=36),
            sa.ForeignKey("sync_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "journal_id",
            sa.Integer(),
            sa.ForeignKey("journals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_category", sa.String(length=50), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "sync_run_id", "journal_id", "source_category", name="uq_sync_run_journal_category"
        ),
    )
    op.create_index("ix_sync_run_journals_sync_run_id", "sync_run_journals", ["sync_run_id"])
    op.create_index("ix_sync_run_journals_journal_id", "sync_run_journals", ["journal_id"])
    op.create_index(
        "ix_sync_run_journals_source_category", "sync_run_journals", ["source_category"]
    )


def downgrade() -> None:
    op.drop_index("ix_sync_run_journals_source_category", table_name="sync_run_journals")
    op.drop_index("ix_sync_run_journals_journal_id", table_name="sync_run_journals")
    op.drop_index("ix_sync_run_journals_sync_run_id", table_name="sync_run_journals")
    op.drop_table("sync_run_journals")

    op.drop_index("ix_article_payloads_article_id_fetched", table_name="article_payloads")
    op.drop_index("ix_article_payloads_checksum", table_name="article_payloads")
    op.drop_index("ix_article_payloads_source_name", table_name="article_payloads")
    op.drop_index("ix_article_payloads_source_category", table_name="article_payloads")
    op.drop_index("ix_article_payloads_journal_id", table_name="article_payloads")
    op.drop_index("ix_article_payloads_article_id", table_name="article_payloads")
    op.drop_table("article_payloads")

    op.drop_index("ix_article_authors_full_name", table_name="article_authors")
    op.drop_index("ix_article_authors_article_id", table_name="article_authors")
    op.drop_table("article_authors")

    op.drop_index("ix_articles_journal_published", table_name="articles")
    op.drop_index("ix_articles_dedup_hash", table_name="articles")
    op.drop_index("ix_articles_source_name", table_name="articles")
    op.drop_index("ix_articles_first_author", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_index("ix_articles_article_type", table_name="articles")
    op.drop_index("ix_articles_source_category", table_name="articles")
    op.drop_index("ix_articles_doi", table_name="articles")
    op.drop_index("ix_articles_title_slug", table_name="articles")
    op.drop_index("ix_articles_title", table_name="articles")
    op.drop_index("ix_articles_journal_id", table_name="articles")
    op.drop_table("articles")

    op.drop_index("ix_sync_runs_started_at", table_name="sync_runs")
    op.drop_table("sync_runs")

    op.drop_index("ix_source_states_source_name", table_name="source_states")
    op.drop_index("ix_source_states_source_category", table_name="source_states")
    op.drop_index("ix_source_states_journal_id", table_name="source_states")
    op.drop_table("source_states")

    op.drop_index("ix_journals_publisher", table_name="journals")
    op.drop_index("ix_journals_journal_name", table_name="journals")
    op.drop_index("ix_journals_slug", table_name="journals")
    op.drop_index("ix_journals_journal_id", table_name="journals")
    op.drop_table("journals")
