"""Persist optional versioned framework-record no-prompt explanations.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE framework_records ADD COLUMN no_prompt_explanation TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE framework_records DROP COLUMN no_prompt_explanation")
