"""Merge the translation and DOI-dedup migration branches.

Revision ID: 20260806_0003
Revises: 20260526_0002, 20260804_0002
Create Date: 2026-08-06 00:00:00.000000
"""

from collections.abc import Sequence

revision: str = "20260806_0003"
down_revision: tuple[str, str] = ("20260526_0002", "20260804_0002")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
