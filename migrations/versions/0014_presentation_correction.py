"""Add append-only presentation-only corrections and issuance supersession.

A project has at most one current issued package. An issued package stops
being current only when an issued presentation-only correction supersedes it.

Revision ID: 0014
Revises: 0013
"""
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# An issuance is current unless an issued correction package supersedes it.
_CURRENT_ISSUANCES = """
    SELECT i.* FROM issuance_snapshots i
    WHERE NOT EXISTS (
        SELECT 1 FROM issuance_supersessions s
        JOIN issuance_snapshots r
          ON r.package_id = s.result_package_id AND r.project_id = s.project_id
        WHERE s.prior_issuance_id = i.id AND s.project_id = i.project_id
    )
"""


def upgrade() -> None:
    duplicate = (
        op.get_bind()
        .execute(
            text(
                """SELECT project_id FROM issuance_snapshots
                   GROUP BY project_id HAVING COUNT(*) > 1 LIMIT 1"""
            )
        )
        .fetchone()
    )
    if duplicate is not None:
        # No supersession evidence exists for pre-correction data, and
        # inventing one would rewrite issued history. Stop rather than guess.
        raise RuntimeError(
            f"Project {duplicate[0]} has more than one issued package without a "
            "recorded supersession; resolve it before upgrading."
        )
    op.execute("""CREATE TABLE package_corrections(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      classification TEXT NOT NULL CHECK(classification = 'presentation_only'),
      unchanged_source_attested INTEGER NOT NULL CHECK(unchanged_source_attested = 1),
      reason TEXT NOT NULL CHECK(trim(reason) != ''),
      prior_package_id TEXT NOT NULL, prior_issuance_id TEXT NOT NULL,
      result_package_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL,
      actor_id TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(id, project_id), UNIQUE(result_package_id),
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(prior_package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(prior_issuance_id, project_id) REFERENCES issuance_snapshots(id, project_id),
      FOREIGN KEY(result_package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id),
      FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
    )""")
    op.execute("""CREATE TABLE issuance_supersessions(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, correction_id TEXT NOT NULL,
      prior_issuance_id TEXT NOT NULL, prior_package_id TEXT NOT NULL,
      result_package_id TEXT NOT NULL, actor_id TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(prior_issuance_id), UNIQUE(correction_id),
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(correction_id, project_id) REFERENCES package_corrections(id, project_id),
      FOREIGN KEY(prior_issuance_id, project_id) REFERENCES issuance_snapshots(id, project_id),
      FOREIGN KEY(prior_package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(result_package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
    )""")
    op.execute(f"CREATE VIEW current_issuances AS {_CURRENT_ISSUANCES}")
    op.execute("""CREATE TRIGGER package_corrections_insert_guard
      BEFORE INSERT ON package_corrections
      WHEN NOT EXISTS (
        SELECT 1 FROM current_issuances i
        JOIN generated_packages prior
          ON prior.id = i.package_id AND prior.project_id = i.project_id
        JOIN generated_packages result
          ON result.id = NEW.result_package_id AND result.project_id = i.project_id
        WHERE i.id = NEW.prior_issuance_id AND i.project_id = NEW.project_id
          AND i.package_id = NEW.prior_package_id
          AND i.assessment_id = NEW.assessment_id
          AND prior.source_snapshot_id = NEW.source_snapshot_id
          AND result.source_snapshot_id = NEW.source_snapshot_id
          AND result.assessment_id = NEW.assessment_id
          AND result.id != prior.id
          AND NOT EXISTS (SELECT 1 FROM issuance_snapshots done
                          WHERE done.package_id = result.id)
      )
      BEGIN SELECT RAISE(ABORT, 'invalid presentation correction binding'); END""")
    op.execute("""CREATE TRIGGER issuance_supersessions_insert_guard
      BEFORE INSERT ON issuance_supersessions
      WHEN NOT EXISTS (
        SELECT 1 FROM package_corrections c
        JOIN current_issuances i
          ON i.id = c.prior_issuance_id AND i.project_id = c.project_id
        WHERE c.id = NEW.correction_id AND c.project_id = NEW.project_id
          AND c.prior_issuance_id = NEW.prior_issuance_id
          AND c.prior_package_id = NEW.prior_package_id
          AND c.result_package_id = NEW.result_package_id
      )
      BEGIN SELECT RAISE(ABORT, 'invalid issuance supersession binding'); END""")
    op.execute("""CREATE TRIGGER issuance_snapshots_one_current
      BEFORE INSERT ON issuance_snapshots
      WHEN EXISTS (
        SELECT 1 FROM current_issuances i
        WHERE i.project_id = NEW.project_id
          AND NOT EXISTS (SELECT 1 FROM issuance_supersessions s
                          WHERE s.prior_issuance_id = i.id
                            AND s.project_id = NEW.project_id
                            AND s.result_package_id = NEW.package_id)
      )
      BEGIN SELECT RAISE(ABORT, 'a project may have only one current issued package'); END""")
    for table in ("package_corrections", "issuance_supersessions"):
        op.execute(f"""CREATE TRIGGER {table}_immutable_update BEFORE UPDATE ON {table}
          BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END""")
        op.execute(f"""CREATE TRIGGER {table}_immutable_delete BEFORE DELETE ON {table}
          BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END""")


def downgrade() -> None:
    if op.get_bind().execute(text("SELECT 1 FROM package_corrections LIMIT 1")).fetchone():
        # Dropping these rows would erase which issued package is current.
        raise RuntimeError("Presentation corrections exist; downgrade would lose issued history.")
    for table in ("issuance_supersessions", "package_corrections"):
        op.execute(f"DROP TRIGGER {table}_immutable_delete")
        op.execute(f"DROP TRIGGER {table}_immutable_update")
    op.execute("DROP TRIGGER issuance_snapshots_one_current")
    op.execute("DROP TRIGGER issuance_supersessions_insert_guard")
    op.execute("DROP TRIGGER package_corrections_insert_guard")
    op.execute("DROP VIEW current_issuances")
    op.execute("DROP TABLE issuance_supersessions")
    op.execute("DROP TABLE package_corrections")
