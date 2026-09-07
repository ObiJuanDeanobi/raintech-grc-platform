"""Add corrective-action lifecycle and immutable binary validation events."""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE corrective_actions ADD COLUMN "
        "validation_state TEXT NOT NULL DEFAULT 'Not Ready' "
        "CHECK(validation_state IN ('Not Ready','Ready','Validated','Failed'))"
    )
    op.execute(
        """
        CREATE TABLE validation_events (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            assessment_id TEXT NOT NULL,
            assessment_revision INTEGER NOT NULL CHECK(assessment_revision > 0),
            record_id TEXT NOT NULL,
            finding_id TEXT NOT NULL,
            corrective_action_id TEXT NOT NULL,
            prior_determination TEXT NOT NULL CHECK(prior_determination = 'Not Met'),
            prior_work_state TEXT NOT NULL CHECK(prior_work_state = 'Ready for Validation'),
            outcome TEXT NOT NULL CHECK(outcome IN ('Validated','Failed')),
            notes TEXT NOT NULL CHECK(length(trim(notes)) > 0),
            actor_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            evidence_context_json TEXT NOT NULL,
            UNIQUE(id, project_id),
            UNIQUE(id, project_id, assessment_id, record_id),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(assessment_id, project_id)
                REFERENCES assessment_revisions(assessment_id, project_id),
            FOREIGN KEY(finding_id, project_id) REFERENCES findings(id, project_id),
            FOREIGN KEY(corrective_action_id, finding_id, project_id)
                REFERENCES corrective_actions(id, finding_id, project_id),
            FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE determination_history (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            assessment_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            prior_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            validation_event_id TEXT NOT NULL,
            FOREIGN KEY(validation_event_id, project_id, assessment_id, record_id)
                REFERENCES validation_events(id, project_id, assessment_id, record_id),
            FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_validation_events_scope "
        "ON validation_events(project_id, assessment_id, record_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_reconciliation_action_single_record "
        "ON not_met_reconciliations(project_id, corrective_action_id) "
        "WHERE corrective_action_id IS NOT NULL"
    )
    for sql in (
        """
        CREATE TRIGGER validation_event_revision_guard
        BEFORE INSERT ON validation_events
        WHEN NEW.assessment_revision != (
            SELECT revision_number FROM assessment_revisions
            WHERE assessment_id = NEW.assessment_id AND project_id = NEW.project_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'Validation event revision must match the assessment');
        END
        """,
        """
        CREATE TRIGGER validation_event_state_guard
        BEFORE INSERT ON validation_events
        WHEN NOT EXISTS (
            SELECT 1 FROM not_met_reconciliations r
            JOIN corrective_actions a
              ON a.id = r.corrective_action_id
             AND a.finding_id = r.finding_id
             AND a.project_id = r.project_id
            JOIN determinations d
              ON d.assessment_id = r.assessment_id AND d.record_id = r.record_id
            WHERE r.project_id = NEW.project_id
              AND r.assessment_id = NEW.assessment_id
              AND r.record_id = NEW.record_id
              AND r.finding_id = NEW.finding_id
              AND r.corrective_action_id = NEW.corrective_action_id
              AND a.status = 'Ready for Validation'
              AND d.status = 'Not Met'
        )
        BEGIN
            SELECT RAISE(ABORT, 'Validation event requires linked Ready for Validation work');
        END
        """,
        """
        CREATE TRIGGER validation_events_no_update BEFORE UPDATE ON validation_events
        BEGIN SELECT RAISE(ABORT, 'Validation events are immutable'); END
        """,
        """
        CREATE TRIGGER validation_events_no_delete BEFORE DELETE ON validation_events
        BEGIN SELECT RAISE(ABORT, 'Validation events are immutable'); END
        """,
        """
        CREATE TRIGGER determination_history_no_update BEFORE UPDATE ON determination_history
        BEGIN SELECT RAISE(ABORT, 'Determination history is immutable'); END
        """,
        """
        CREATE TRIGGER determination_history_no_delete BEFORE DELETE ON determination_history
        BEGIN SELECT RAISE(ABORT, 'Determination history is immutable'); END
        """,
        """
        CREATE TRIGGER corrective_action_no_direct_close
        BEFORE UPDATE OF status ON corrective_actions
        WHEN NEW.status = 'Closed' AND OLD.status != 'Closed'
          AND NOT EXISTS (
              SELECT 1 FROM validation_events e
              JOIN not_met_reconciliations r
                ON r.project_id = e.project_id
               AND r.assessment_id = e.assessment_id
               AND r.record_id = e.record_id
               AND r.finding_id = e.finding_id
               AND r.corrective_action_id = e.corrective_action_id
              WHERE e.project_id = NEW.project_id AND e.finding_id = NEW.finding_id
                AND e.corrective_action_id = NEW.id AND e.outcome = 'Validated'
          )
        BEGIN SELECT RAISE(ABORT, 'Corrective actions close only through validation'); END
        """,
        """
        CREATE TRIGGER determination_no_unvalidated_met
        BEFORE UPDATE OF status ON determinations
        WHEN NEW.status = 'Met' AND OLD.status = 'Not Met'
          AND EXISTS (
              SELECT 1 FROM not_met_reconciliations
              WHERE assessment_id = NEW.assessment_id AND record_id = NEW.record_id
                AND corrective_action_id IS NOT NULL
          )
          AND NOT EXISTS (
              SELECT 1 FROM validation_events e
              JOIN assessment_revisions ar
                ON ar.assessment_id = e.assessment_id AND ar.project_id = e.project_id
              WHERE e.assessment_id = NEW.assessment_id AND e.record_id = NEW.record_id
                AND e.project_id = ar.project_id AND e.outcome = 'Validated'
          )
        BEGIN SELECT RAISE(ABORT, 'Linked Not Met work requires validation before Met'); END
        """,
    ):
        op.execute(sql)


def downgrade() -> None:
    for name in (
        "determination_no_unvalidated_met",
        "corrective_action_no_direct_close",
        "determination_history_no_delete",
        "determination_history_no_update",
        "validation_events_no_delete",
        "validation_events_no_update",
        "validation_event_state_guard",
        "validation_event_revision_guard",
    ):
        op.execute(f"DROP TRIGGER {name}")
    op.execute("DROP TABLE determination_history")
    op.execute("DROP TABLE validation_events")
    op.execute("DROP INDEX idx_reconciliation_action_single_record")
    op.execute("ALTER TABLE corrective_actions DROP COLUMN validation_state")
