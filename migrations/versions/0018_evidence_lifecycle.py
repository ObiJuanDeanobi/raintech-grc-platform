"""Add evidence recycle bin, purge marker, and review date.

A binned artifact cannot gain mappings. Purging removes stored bytes only; the
artifact and its immutable version rows and hashes remain.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("deleted_at", "purged_at", "review_date"):
        op.execute(f"ALTER TABLE evidence_artifacts ADD COLUMN {column} TEXT")
    op.execute(
        """CREATE TRIGGER evidence_mappings_not_binned
        BEFORE INSERT ON evidence_mappings
        WHEN (SELECT deleted_at FROM evidence_artifacts WHERE id = NEW.artifact_id) IS NOT NULL
        BEGIN SELECT RAISE(ABORT, 'binned evidence cannot be mapped'); END"""
    )


def downgrade() -> None:
    if op.get_bind().execute(
        text("SELECT 1 FROM evidence_artifacts WHERE deleted_at IS NOT NULL LIMIT 1")
    ).fetchone():
        raise RuntimeError("Binned evidence exists; downgrade would restore it silently.")
    op.execute("DROP TRIGGER evidence_mappings_not_binned")
    for column in ("review_date", "purged_at", "deleted_at"):
        op.execute(f"ALTER TABLE evidence_artifacts DROP COLUMN {column}")
