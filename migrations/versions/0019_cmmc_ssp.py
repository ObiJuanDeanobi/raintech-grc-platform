"""Add the CMMC System Security Plan: generated documents, versions, approval.

An SSP pins its source snapshot and template version. Edits append versions;
approval freezes the document, after which no version may be added.

Revision ID: 0019
Revises: 0018
"""
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMMUTABLE = ("ssp_documents", "ssp_versions", "ssp_approvals")


def upgrade() -> None:
    op.execute(
        """CREATE TABLE ssp_documents (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
        template_version TEXT NOT NULL, template_sha256 TEXT NOT NULL,
        source_json TEXT NOT NULL, source_sha256 TEXT NOT NULL,
        created_by TEXT NOT NULL REFERENCES user_accounts(id), created_at TEXT NOT NULL,
        UNIQUE(id, project_id),
        FOREIGN KEY(assessment_id, project_id) REFERENCES assessments(id, project_id))"""
    )
    op.execute(
        """CREATE TABLE ssp_versions (
        id TEXT PRIMARY KEY, ssp_id TEXT NOT NULL, project_id TEXT NOT NULL,
        version_number INTEGER NOT NULL, content_json TEXT NOT NULL,
        content_sha256 TEXT NOT NULL, note TEXT NOT NULL,
        created_by TEXT NOT NULL REFERENCES user_accounts(id), created_at TEXT NOT NULL,
        UNIQUE(ssp_id, version_number),
        FOREIGN KEY(ssp_id, project_id) REFERENCES ssp_documents(id, project_id))"""
    )
    op.execute(
        """CREATE TABLE ssp_approvals (
        id TEXT PRIMARY KEY, ssp_id TEXT NOT NULL UNIQUE, ssp_version_id TEXT NOT NULL,
        project_id TEXT NOT NULL, approver_id TEXT NOT NULL REFERENCES user_accounts(id),
        approved_at TEXT NOT NULL,
        FOREIGN KEY(ssp_id, project_id) REFERENCES ssp_documents(id, project_id),
        FOREIGN KEY(ssp_version_id) REFERENCES ssp_versions(id))"""
    )
    for table in IMMUTABLE:
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"""CREATE TRIGGER {table}_immutable_{action.lower()} BEFORE {action} ON {table}
                BEGIN SELECT RAISE(ABORT, '{table} rows are immutable'); END"""
            )
    op.execute(
        """CREATE TRIGGER ssp_versions_frozen_after_approval BEFORE INSERT ON ssp_versions
        WHEN EXISTS (SELECT 1 FROM ssp_approvals WHERE ssp_id = NEW.ssp_id)
        BEGIN SELECT RAISE(ABORT, 'an approved SSP is frozen'); END"""
    )
    op.execute(
        """CREATE TRIGGER ssp_approvals_latest_version BEFORE INSERT ON ssp_approvals
        WHEN NEW.ssp_version_id != (SELECT id FROM ssp_versions WHERE ssp_id = NEW.ssp_id
                                    ORDER BY version_number DESC LIMIT 1)
        BEGIN SELECT RAISE(ABORT, 'only the latest SSP version can be approved'); END"""
    )


def downgrade() -> None:
    if op.get_bind().execute(text("SELECT 1 FROM ssp_documents LIMIT 1")).fetchone():
        raise RuntimeError("SSP documents exist; downgrade would lose approved SSP history.")
    op.execute("DROP TRIGGER ssp_approvals_latest_version")
    op.execute("DROP TRIGGER ssp_versions_frozen_after_approval")
    for table in IMMUTABLE:
        for action in ("update", "delete"):
            op.execute(f"DROP TRIGGER {table}_immutable_{action}")
    for table in reversed(IMMUTABLE):
        op.execute(f"DROP TABLE {table}")
