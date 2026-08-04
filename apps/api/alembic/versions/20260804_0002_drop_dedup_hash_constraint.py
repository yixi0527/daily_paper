"""Drop the legacy title-based article uniqueness constraint.

Revision ID: 20260804_0002
Revises: 20260419_0001
Create Date: 2026-08-04 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_0002"
down_revision: str | None = "20260419_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_articles_dedup_hash", "articles", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("uq_articles_dedup_hash", "articles", ["dedup_hash"])
