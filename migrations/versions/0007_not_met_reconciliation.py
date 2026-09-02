"""Add project-scoped Not Met findings, corrective actions, and reconciliation."""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_assessments_id_project ON assessments(id, project_id)"
    )
    for sql in (
        """
      CREATE TABLE findings (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Open',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(id, project_id), FOREIGN KEY(project_id) REFERENCES projects(id))
    """,
        """
      CREATE TABLE corrective_actions (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, finding_id TEXT NOT NULL,
        title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Open',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(id, project_id), UNIQUE(id, finding_id, project_id),
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(finding_id, project_id) REFERENCES findings(id, project_id))
    """,
        """
      CREATE TABLE not_met_reconciliations (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
        record_id TEXT NOT NULL,
        outcome TEXT NOT NULL
            CHECK(outcome IN ('create','link_existing','not_needed')),
        finding_id TEXT, corrective_action_id TEXT, rationale TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(assessment_id, record_id),
        UNIQUE(id, project_id, assessment_id, record_id),
        FOREIGN KEY(assessment_id, project_id) REFERENCES assessments(id, project_id),
        FOREIGN KEY(finding_id, project_id) REFERENCES findings(id, project_id),
        FOREIGN KEY(corrective_action_id, finding_id, project_id)
            REFERENCES corrective_actions(id, finding_id, project_id),
        CHECK(
            (outcome = 'not_needed' AND finding_id IS NULL
                AND corrective_action_id IS NULL AND length(trim(rationale)) > 0)
            OR
            (outcome IN ('create', 'link_existing') AND finding_id IS NOT NULL
                AND corrective_action_id IS NOT NULL)
        ))
    """,
        """
      CREATE TABLE not_met_reconciliation_history (
        id TEXT PRIMARY KEY, reconciliation_id TEXT NOT NULL, project_id TEXT NOT NULL,
        assessment_id TEXT NOT NULL, record_id TEXT NOT NULL, outcome TEXT NOT NULL,
        finding_id TEXT, corrective_action_id TEXT, rationale TEXT NOT NULL, actor_id TEXT NOT NULL,
        changed_at TEXT NOT NULL,
        FOREIGN KEY(reconciliation_id, project_id, assessment_id, record_id)
            REFERENCES not_met_reconciliations(id, project_id, assessment_id, record_id),
        FOREIGN KEY(finding_id, project_id) REFERENCES findings(id, project_id),
        FOREIGN KEY(corrective_action_id, finding_id, project_id)
            REFERENCES corrective_actions(id, finding_id, project_id))
    """,
        """
        CREATE INDEX idx_reconciliation_project
        ON not_met_reconciliations(project_id, assessment_id, record_id)
        """,
        """
        CREATE TRIGGER reconciliation_history_append_only_update
        BEFORE UPDATE ON not_met_reconciliation_history
        BEGIN
            SELECT RAISE(ABORT, 'Reconciliation history is append-only');
        END
        """,
        """
        CREATE TRIGGER reconciliation_history_append_only_delete
        BEFORE DELETE ON not_met_reconciliation_history
        BEGIN
            SELECT RAISE(ABORT, 'Reconciliation history is append-only');
        END
        """,
    ):
        op.execute(sql)


def downgrade() -> None:
    for name in (
        "reconciliation_history_append_only_delete",
        "reconciliation_history_append_only_update",
    ):
        op.execute(f"DROP TRIGGER {name}")
    for name in (
        "not_met_reconciliation_history",
        "not_met_reconciliations",
        "corrective_actions",
        "findings",
    ):
        op.execute(f"DROP TABLE {name}")
    op.execute("DROP INDEX IF EXISTS uq_assessments_id_project")
