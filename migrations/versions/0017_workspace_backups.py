"""Add workspace backup records for Back Up Now and automatic daily/weekly sets.

Pre-issuance backups stay in backup_records. Pruned sets keep their record
with status 'pruned' so retention is auditable.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE workspace_backups (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL CHECK(kind IN ('daily', 'weekly', 'manual')),
        status TEXT NOT NULL CHECK(status IN ('complete', 'failed', 'pruned')),
        relative_path TEXT, manifest_sha256 TEXT, archive_sha256 TEXT, bytes INTEGER,
        actor_id TEXT NOT NULL REFERENCES user_accounts(id),
        started_at TEXT NOT NULL, completed_at TEXT NOT NULL, failure TEXT NOT NULL DEFAULT '',
        CHECK((status = 'failed') = (relative_path IS NULL)))"""
    )
    op.execute("CREATE INDEX idx_workspace_backups_kind ON workspace_backups(kind, started_at)")


def downgrade() -> None:
    op.execute("DROP TABLE workspace_backups")
