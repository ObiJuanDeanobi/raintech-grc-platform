"""Add immutable governed report generation records."""  # noqa: E501
# ruff: noqa: E501, I001

from collections.abc import Sequence
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE source_snapshots (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      assessment_revision INTEGER NOT NULL, profile_version_id TEXT, revision_token TEXT NOT NULL,
      source_json TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      UNIQUE(id, project_id)
    )
    """)
    op.execute("""
    CREATE TABLE generation_attempts (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      target TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('staged','promoted','failed')),
      source_snapshot_id TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL, completed_at TEXT,
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id),
      UNIQUE(id, project_id)
    )
    """)
    op.execute("""
    CREATE TABLE generated_packages (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      generation_attempt_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL,
      template_version TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('staged','promoted')),
      manifest_json TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(generation_attempt_id, project_id) REFERENCES generation_attempts(id, project_id),
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id)
      , UNIQUE(id, project_id)
    )
    """)
    op.execute("""
    CREATE TABLE generated_components (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, package_id TEXT NOT NULL,
      kind TEXT NOT NULL, filename TEXT NOT NULL, relative_path TEXT NOT NULL,
      sha256 TEXT NOT NULL, byte_count INTEGER NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(package_id, project_id) REFERENCES generated_packages(id, project_id),
      UNIQUE(id, project_id), UNIQUE(package_id, project_id, kind)
    )
    """)
    op.execute(
        "CREATE INDEX idx_source_snapshots_project ON source_snapshots(project_id, assessment_id)"
    )
    op.execute(
        "CREATE INDEX idx_generation_attempts_project ON generation_attempts(project_id, assessment_id)"
    )
    op.execute(
        "CREATE INDEX idx_generated_packages_project ON generated_packages(project_id, assessment_id)"
    )
    op.execute(
        "CREATE INDEX idx_generated_components_project ON generated_components(project_id, package_id)"
    )
    op.execute("""CREATE TRIGGER generation_attempts_guard BEFORE UPDATE ON generation_attempts
      WHEN NOT (OLD.state='staged' AND NEW.state IN ('promoted','failed') AND NEW.id=OLD.id
        AND NEW.project_id=OLD.project_id AND NEW.assessment_id=OLD.assessment_id
        AND NEW.target=OLD.target AND NEW.source_snapshot_id=OLD.source_snapshot_id
        AND (NEW.error IS OLD.error OR NEW.state='failed'))
      BEGIN SELECT RAISE(ABORT, 'generation attempts are immutable'); END""")
    op.execute("""CREATE TRIGGER generated_packages_guard BEFORE UPDATE ON generated_packages
      WHEN NOT (OLD.state='staged' AND NEW.state='promoted' AND NEW.id=OLD.id
        AND NEW.project_id=OLD.project_id AND NEW.assessment_id=OLD.assessment_id
        AND NEW.generation_attempt_id=OLD.generation_attempt_id AND NEW.source_snapshot_id=OLD.source_snapshot_id
        AND NEW.template_version=OLD.template_version AND NEW.manifest_json=OLD.manifest_json
        AND NEW.sha256=OLD.sha256 AND NEW.created_at=OLD.created_at)
      BEGIN SELECT RAISE(ABORT, 'generated packages are immutable'); END""")
    for table in ("source_snapshots", "generated_components"):
        op.execute(
            f"CREATE TRIGGER {table}_append_only_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END"
        )
    for table in (
        "source_snapshots",
        "generation_attempts",
        "generated_packages",
        "generated_components",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_append_only_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END"
        )


def downgrade() -> None:
    for table in (
        "generated_components",
        "generated_packages",
        "generation_attempts",
        "source_snapshots",
    ):
        op.execute(f"DROP TRIGGER {table}_append_only_delete")
    op.execute("DROP TRIGGER generation_attempts_guard")
    op.execute("DROP TRIGGER generated_packages_guard")
    for table in ("source_snapshots", "generated_components"):
        op.execute(f"DROP TRIGGER {table}_append_only_update")
    for table in (
        "generated_components",
        "generated_packages",
        "generation_attempts",
        "source_snapshots",
    ):
        op.execute(f"DROP TABLE {table}")
