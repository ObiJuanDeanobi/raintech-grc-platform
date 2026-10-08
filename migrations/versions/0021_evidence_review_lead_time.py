"""Add the project-level evidence review warning lead time (GitHub issue #142).

Evidence within this many days of its review date shows as due soon; once the
review date has passed it is stale and no longer verifies a Met. Staleness is
computed on read, so no other schema changes. The default is 30 days
(specification, Recurring Reviews: default reminder lead time).

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE projects ADD COLUMN evidence_review_lead_days INTEGER NOT NULL DEFAULT 30"
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(text("SELECT 1 FROM projects WHERE evidence_review_lead_days != 30 LIMIT 1"))
        .fetchone()
    ):
        raise RuntimeError(
            "A project has a custom evidence lead time; downgrade would discard it silently."
        )
    op.execute("ALTER TABLE projects DROP COLUMN evidence_review_lead_days")
