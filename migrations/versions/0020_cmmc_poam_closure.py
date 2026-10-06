"""Allow a CMMC POA&M item to close once its requirement derives Met.

HIPAA corrective actions close only through a validation event tied to a
Not Met reconciliation. CMMC findings are requirement-level and have no
reconciliation row, so they close through an append-only POA&M closure record
instead. The API records one only while the requirement derives Met.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VALIDATED = """EXISTS (
              SELECT 1 FROM validation_events e
              JOIN not_met_reconciliations r
                ON r.project_id = e.project_id
               AND r.assessment_id = e.assessment_id
               AND r.record_id = e.record_id
               AND r.finding_id = e.finding_id
               AND r.corrective_action_id = e.corrective_action_id
              WHERE e.project_id = NEW.project_id AND e.finding_id = NEW.finding_id
                AND e.corrective_action_id = NEW.id AND e.outcome = 'Validated'
          )"""
_CLOSED_BY_CMMC = """EXISTS (
              SELECT 1 FROM poam_closures c
              WHERE c.corrective_action_id = NEW.id AND c.project_id = NEW.project_id
          )"""


def _trigger(condition: str) -> str:
    return f"""CREATE TRIGGER corrective_action_no_direct_close
        BEFORE UPDATE OF status ON corrective_actions
        WHEN NEW.status = 'Closed' AND OLD.status != 'Closed'
          AND NOT {condition}
        BEGIN SELECT RAISE(ABORT, 'Corrective actions close only through validation'); END"""


def upgrade() -> None:
    op.execute(
        """CREATE TABLE poam_closures (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
        corrective_action_id TEXT NOT NULL UNIQUE, finding_id TEXT NOT NULL,
        assessment_id TEXT NOT NULL, record_id TEXT NOT NULL,
        rationale TEXT NOT NULL CHECK(length(trim(rationale)) > 0),
        closed_by TEXT NOT NULL REFERENCES user_accounts(id), closed_at TEXT NOT NULL,
        FOREIGN KEY(corrective_action_id, finding_id, project_id)
            REFERENCES corrective_actions(id, finding_id, project_id),
        FOREIGN KEY(project_id, record_id) REFERENCES requirement_findings(project_id, record_id),
        FOREIGN KEY(assessment_id, project_id) REFERENCES assessments(id, project_id))"""
    )
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"""CREATE TRIGGER poam_closures_immutable_{action.lower()}
            BEFORE {action} ON poam_closures
            BEGIN SELECT RAISE(ABORT, 'POA&M closures are immutable'); END"""
        )
    op.execute("DROP TRIGGER corrective_action_no_direct_close")
    op.execute(_trigger(f"({_VALIDATED} OR {_CLOSED_BY_CMMC})"))


def downgrade() -> None:
    if op.get_bind().execute(text("SELECT 1 FROM poam_closures LIMIT 1")).fetchone():
        raise RuntimeError("POA&M closures exist; downgrade would reopen closed CMMC work.")
    op.execute("DROP TRIGGER corrective_action_no_direct_close")
    op.execute(_trigger(_VALIDATED))
    op.execute("DROP TRIGGER poam_closures_immutable_update")
    op.execute("DROP TRIGGER poam_closures_immutable_delete")
    op.execute("DROP TABLE poam_closures")
