"""article translation and library-linked analysis"""

import sqlalchemy as sa
from alembic import op

revision = "20260526_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("title_zh", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("abstract_zh", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("related_literature", sa.JSON(), nullable=True))
    op.add_column(
        "articles", sa.Column("related_literature_notes_zh", sa.JSON(), nullable=True)
    )
    op.add_column("articles", sa.Column("heuristic_thoughts_zh", sa.JSON(), nullable=True))
    op.add_column("articles", sa.Column("analysis_model", sa.String(length=120), nullable=True))
    op.add_column(
        "articles", sa.Column("analysis_generated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("articles", "analysis_generated_at")
    op.drop_column("articles", "analysis_model")
    op.drop_column("articles", "heuristic_thoughts_zh")
    op.drop_column("articles", "related_literature_notes_zh")
    op.drop_column("articles", "related_literature")
    op.drop_column("articles", "abstract_zh")
    op.drop_column("articles", "title_zh")
