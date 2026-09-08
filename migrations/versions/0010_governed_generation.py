"""Add immutable governed report generation records."""
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
      UNIQUE(id, project_id), UNIQUE(project_id, assessment_id, revision_token)
    )
    """)
    op.execute("""
    CREATE TABLE generation_attempts (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      target TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('staged','promoted','failed')),
      source_snapshot_id TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL, completed_at TEXT,
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id)
    )
    """)
    op.execute("""
    CREATE TABLE generated_packages (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      generation_attempt_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL,
      template_version TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('staged','promoted')),
      manifest_json TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(generation_attempt_id) REFERENCES generation_attempts(id),
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id)
    )
    """)
    op.execute("""
    CREATE TABLE generated_components (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, package_id TEXT NOT NULL,
      kind TEXT NOT NULL, filename TEXT NOT NULL, relative_path TEXT NOT NULL,
      sha256 TEXT NOT NULL, byte_count INTEGER NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(package_id) REFERENCES generated_packages(id)
    )
    """)
    op.execute("CREATE INDEX idx_source_snapshots_project ON source_snapshots(project_id, assessment_id)")
    op.execute("CREATE INDEX idx_generation_attempts_project ON generation_attempts(project_id, assessment_id)")
    op.execute("CREATE INDEX idx_generated_packages_project ON generated_packages(project_id, assessment_id)")
    op.execute("CREATE INDEX idx_generated_components_project ON generated_components(project_id, package_id)")

def downgrade() -> None:
    for table in ("generated_components", "generated_packages", "generation_attempts", "source_snapshots"):
        op.execute(f"DROP TABLE {table}")
