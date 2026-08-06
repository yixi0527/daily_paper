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
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_constraint("uq_articles_dedup_hash", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.create_unique_constraint("uq_articles_dedup_hash", ["dedup_hash"])
