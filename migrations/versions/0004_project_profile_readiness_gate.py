"""Project-scoped profile readiness gate.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-26 19:57:04.165763
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE profile_boundary_acknowledgements (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL UNIQUE REFERENCES projects(id),
            document_path TEXT NOT NULL,
            actor_id TEXT NOT NULL REFERENCES user_accounts(id),
            created_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE profile_readiness_transitions (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            prior_state TEXT NOT NULL,
            next_state TEXT NOT NULL,
            actor_id TEXT NOT NULL REFERENCES user_accounts(id),
            decision_note TEXT NOT NULL,
            unresolved_required_fields_json TEXT NOT NULL DEFAULT '[]',
            follow_up_work TEXT NOT NULL DEFAULT '',
            reviewed_by TEXT NOT NULL DEFAULT '',
            approval_evidence TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            CHECK (prior_state IN (
                'Intake started', 'Intake complete', 'Needs follow-up', 'Profile complete'
            )),
            CHECK (next_state IN (
                'Intake started', 'Intake complete', 'Needs follow-up', 'Profile complete'
            ))
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_profile_readiness_transitions_project "
        "ON profile_readiness_transitions(project_id, created_at)"
    )
    op.execute(
        """
        CREATE TRIGGER profile_readiness_transitions_must_be_continuous
        BEFORE INSERT ON profile_readiness_transitions
        WHEN (
            NOT EXISTS (
                SELECT 1 FROM profile_readiness_transitions
                WHERE project_id = NEW.project_id
            ) AND NEW.prior_state != NEW.next_state
        ) OR (
            EXISTS (
                SELECT 1 FROM profile_readiness_transitions
                WHERE project_id = NEW.project_id
            ) AND NEW.prior_state != (
                SELECT next_state FROM profile_readiness_transitions
                WHERE project_id = NEW.project_id
                ORDER BY rowid DESC
                LIMIT 1
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'Profile readiness transitions must be continuous');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_readiness_transitions_cannot_change
        BEFORE UPDATE ON profile_readiness_transitions
        BEGIN
            SELECT RAISE(ABORT, 'Profile readiness transitions are append-only');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_readiness_transitions_cannot_delete
        BEFORE DELETE ON profile_readiness_transitions
        BEGIN
            SELECT RAISE(ABORT, 'Profile readiness transitions are append-only');
        END
        """
    )
    connection = op.get_bind()
    projects = connection.exec_driver_sql(
        "SELECT id, created_at FROM projects ORDER BY created_at, id"
    ).mappings()
    for project in projects:
        connection.exec_driver_sql(
            """
            INSERT INTO profile_readiness_transitions(
                id, project_id, prior_state, next_state, actor_id, decision_note,
                unresolved_required_fields_json, follow_up_work, reviewed_by,
                approval_evidence, created_at
            ) VALUES (?, ?, 'Intake started', 'Intake started', 'johnathan',
                      'Profile readiness initialized.', '[]', '', '', '', ?)
            """,
            (str(uuid4()), project["id"], project["created_at"]),
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER profile_readiness_transitions_cannot_delete")
    op.execute("DROP TRIGGER profile_readiness_transitions_cannot_change")
    op.execute("DROP TRIGGER profile_readiness_transitions_must_be_continuous")
    op.execute("DROP INDEX idx_profile_readiness_transitions_project")
    op.execute("DROP TABLE profile_readiness_transitions")
    op.execute("DROP TABLE profile_boundary_acknowledgements")
