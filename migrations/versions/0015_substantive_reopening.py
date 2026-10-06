"""Add substantive reopening of an issued assessment and revalidation items.

A reopening records why an issued assessment was reopened, which records are
affected, and the successor assessment created for it. The prior issue stays
current until a package generated from that successor is issued.

Revision ID: 0015
Revises: 0014
"""
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_0014 = """
    SELECT i.* FROM issuance_snapshots i
    WHERE NOT EXISTS (
        SELECT 1 FROM issuance_supersessions s
        JOIN issuance_snapshots r
          ON r.package_id = s.result_package_id AND r.project_id = s.project_id
        WHERE s.prior_issuance_id = i.id AND s.project_id = i.project_id
    )
"""
# An issue is also superseded once its reopening's successor assessment is issued.
_CURRENT_0015 = (
    _CURRENT_0014
    + """
    AND NOT EXISTS (
        SELECT 1 FROM assessment_reopenings o
        JOIN issuance_snapshots r
          ON r.assessment_id = o.successor_assessment_id AND r.project_id = o.project_id
        WHERE o.prior_issuance_id = i.id AND o.project_id = i.project_id
    )
"""
)
_ONE_CURRENT_0014 = """CREATE TRIGGER issuance_snapshots_one_current
      BEFORE INSERT ON issuance_snapshots
      WHEN EXISTS (
        SELECT 1 FROM current_issuances i
        WHERE i.project_id = NEW.project_id
          AND NOT EXISTS (SELECT 1 FROM issuance_supersessions s
                          WHERE s.prior_issuance_id = i.id
                            AND s.project_id = NEW.project_id
                            AND s.result_package_id = NEW.package_id)
      )
      BEGIN SELECT RAISE(ABORT, 'a project may have only one current issued package'); END"""
_ONE_CURRENT_0015 = """CREATE TRIGGER issuance_snapshots_one_current
      BEFORE INSERT ON issuance_snapshots
      WHEN EXISTS (
        SELECT 1 FROM current_issuances i
        WHERE i.project_id = NEW.project_id
          AND NOT EXISTS (SELECT 1 FROM issuance_supersessions s
                          WHERE s.prior_issuance_id = i.id
                            AND s.project_id = NEW.project_id
                            AND s.result_package_id = NEW.package_id)
          AND NOT EXISTS (SELECT 1 FROM assessment_reopenings o
                          WHERE o.prior_issuance_id = i.id
                            AND o.project_id = NEW.project_id
                            AND o.successor_assessment_id = NEW.assessment_id)
      )
      BEGIN SELECT RAISE(ABORT, 'a project may have only one current issued package'); END"""


def _swap_current(view: str, trigger: str) -> None:
    op.execute("DROP TRIGGER issuance_snapshots_one_current")
    op.execute("DROP VIEW current_issuances")
    op.execute(f"CREATE VIEW current_issuances AS {view}")
    op.execute(trigger)


def upgrade() -> None:
    op.execute("""CREATE TABLE assessment_reopenings(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
      classification TEXT NOT NULL CHECK(classification = 'substantive'),
      rationale TEXT NOT NULL CHECK(trim(rationale) != ''),
      affected_record_ids_json TEXT NOT NULL
        CHECK(json_valid(affected_record_ids_json)
              AND json_type(affected_record_ids_json) = 'array'
              AND json_array_length(affected_record_ids_json) > 0),
      predecessor_assessment_id TEXT NOT NULL, successor_assessment_id TEXT NOT NULL,
      prior_package_id TEXT NOT NULL, prior_issuance_id TEXT NOT NULL,
      actor_id TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(id, project_id), UNIQUE(successor_assessment_id), UNIQUE(prior_issuance_id),
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(predecessor_assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(successor_assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(prior_package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(prior_issuance_id, project_id) REFERENCES issuance_snapshots(id, project_id),
      FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
    )""")
    op.execute("""CREATE TABLE revalidation_items(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, reopening_id TEXT NOT NULL,
      assessment_id TEXT NOT NULL, record_id TEXT NOT NULL,
      revalidated_by TEXT, revalidated_at TEXT, note TEXT NOT NULL DEFAULT '',
      UNIQUE(assessment_id, record_id),
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(reopening_id, project_id) REFERENCES assessment_reopenings(id, project_id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(revalidated_by) REFERENCES user_accounts(id),
      CHECK((revalidated_by IS NULL) = (revalidated_at IS NULL)),
      CHECK(revalidated_by IS NULL OR trim(note) != '')
    )""")
    op.execute("""CREATE TRIGGER assessment_reopenings_insert_guard
      BEFORE INSERT ON assessment_reopenings
      WHEN NOT EXISTS (
        SELECT 1 FROM current_issuances i
        JOIN assessment_revisions s
          ON s.assessment_id = NEW.successor_assessment_id AND s.project_id = i.project_id
        JOIN project_active_assessments a
          ON a.project_id = i.project_id AND a.assessment_id = s.assessment_id
        WHERE i.id = NEW.prior_issuance_id AND i.project_id = NEW.project_id
          AND i.package_id = NEW.prior_package_id
          AND i.assessment_id = NEW.predecessor_assessment_id
          AND s.predecessor_assessment_id = NEW.predecessor_assessment_id
      )
      BEGIN SELECT RAISE(ABORT, 'invalid substantive reopening binding'); END""")
    op.execute("""CREATE TRIGGER revalidation_items_insert_guard
      BEFORE INSERT ON revalidation_items
      WHEN NEW.revalidated_by IS NOT NULL OR NOT EXISTS (
        SELECT 1 FROM assessment_reopenings o, json_each(o.affected_record_ids_json) r
        WHERE o.id = NEW.reopening_id AND o.project_id = NEW.project_id
          AND o.successor_assessment_id = NEW.assessment_id AND r.value = NEW.record_id
      )
      BEGIN SELECT RAISE(ABORT, 'invalid revalidation item'); END""")
    # Revalidation is recorded once; the item is otherwise immutable.
    op.execute("""CREATE TRIGGER revalidation_items_resolve_once
      BEFORE UPDATE ON revalidation_items
      WHEN OLD.revalidated_by IS NOT NULL OR NEW.revalidated_by IS NULL
        OR NEW.id != OLD.id OR NEW.project_id != OLD.project_id
        OR NEW.reopening_id != OLD.reopening_id OR NEW.assessment_id != OLD.assessment_id
        OR NEW.record_id != OLD.record_id
        OR NEW.assessment_id != (SELECT assessment_id FROM project_active_assessments
                                 WHERE project_id = NEW.project_id)
      BEGIN SELECT RAISE(ABORT, 'revalidation items are resolved once'); END""")
    op.execute("""CREATE TRIGGER revalidation_items_immutable_delete
      BEFORE DELETE ON revalidation_items
      BEGIN SELECT RAISE(ABORT, 'revalidation_items are immutable'); END""")
    op.execute("""CREATE TRIGGER assessment_reopenings_immutable_update
      BEFORE UPDATE ON assessment_reopenings
      BEGIN SELECT RAISE(ABORT, 'assessment_reopenings are immutable'); END""")
    op.execute("""CREATE TRIGGER assessment_reopenings_immutable_delete
      BEFORE DELETE ON assessment_reopenings
      BEGIN SELECT RAISE(ABORT, 'assessment_reopenings are immutable'); END""")
    _swap_current(_CURRENT_0015, _ONE_CURRENT_0015)
    # A reopened assessment references the same corrective action as its predecessor,
    # so the one-record-per-action rule becomes per assessment, and a trigger keeps an
    # action tied to one record across every revision.
    op.execute("DROP INDEX idx_reconciliation_action_single_record")
    op.execute(
        """CREATE UNIQUE INDEX idx_reconciliation_action_single_record
        ON not_met_reconciliations(project_id, assessment_id, corrective_action_id)
        WHERE corrective_action_id IS NOT NULL"""
    )
    for event, column in (("insert", ""), ("update", "OF corrective_action_id, record_id")):
        op.execute(f"""CREATE TRIGGER reconciliation_action_single_record_{event}
          BEFORE {event.upper()} {column} ON not_met_reconciliations
          WHEN NEW.corrective_action_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM not_met_reconciliations r
            WHERE r.project_id = NEW.project_id
              AND r.corrective_action_id = NEW.corrective_action_id
              AND r.record_id != NEW.record_id)
          BEGIN SELECT RAISE(ABORT, 'a corrective action belongs to one record'); END""")


def downgrade() -> None:
    if op.get_bind().execute(text("SELECT 1 FROM assessment_reopenings LIMIT 1")).fetchone():
        raise RuntimeError("Substantive reopenings exist; downgrade would lose issued history.")
    op.execute("DROP TRIGGER reconciliation_action_single_record_update")
    op.execute("DROP TRIGGER reconciliation_action_single_record_insert")
    op.execute("DROP INDEX idx_reconciliation_action_single_record")
    op.execute(
        """CREATE UNIQUE INDEX idx_reconciliation_action_single_record
        ON not_met_reconciliations(project_id, corrective_action_id)
        WHERE corrective_action_id IS NOT NULL"""
    )
    _swap_current(_CURRENT_0014, _ONE_CURRENT_0014)
    for name in (
        "assessment_reopenings_immutable_delete",
        "assessment_reopenings_immutable_update",
        "revalidation_items_immutable_delete",
        "revalidation_items_resolve_once",
        "revalidation_items_insert_guard",
        "assessment_reopenings_insert_guard",
    ):
        op.execute(f"DROP TRIGGER {name}")
    op.execute("DROP TABLE revalidation_items")
    op.execute("DROP TABLE assessment_reopenings")
