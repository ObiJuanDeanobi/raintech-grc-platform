"""Project-scoped immutable initial evidence versions.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    artifacts = connection.exec_driver_sql(
        """
        SELECT id, project_id, relative_path, created_at
        FROM evidence_artifacts
        ORDER BY id
        """
    ).mappings().all()
    versions: list[tuple[str, str, str, int, str, str, str]] = []
    if artifacts:
        storage_root_option = op.get_context().config.get_main_option(
            "raintech.managed_storage_root"
        )
        if not storage_root_option:
            raise RuntimeError(
                "Cannot backfill evidence versions without the managed storage root"
            )
        storage_root = Path(storage_root_option).resolve()
        for artifact in artifacts:
            relative_path = Path(artifact["relative_path"])
            stored_file = (storage_root / relative_path).resolve()
            try:
                stored_file.relative_to(storage_root)
            except ValueError as error:
                raise RuntimeError(
                    f"Cannot backfill evidence version outside managed storage: {relative_path}"
                ) from error
            if not stored_file.is_file():
                raise RuntimeError(
                    f"Cannot backfill evidence version; stored file is missing: {relative_path}"
                )
            versions.append(
                (
                    f"{artifact['id']}:1",
                    artifact["id"],
                    artifact["project_id"],
                    1,
                    artifact["relative_path"],
                    sha256(stored_file.read_bytes()).hexdigest(),
                    artifact["created_at"],
                )
            )
    op.execute(
        """
        CREATE TABLE evidence_versions (
            id TEXT PRIMARY KEY,
            artifact_id TEXT NOT NULL REFERENCES evidence_artifacts(id),
            project_id TEXT NOT NULL REFERENCES projects(id),
            version_number INTEGER NOT NULL,
            relative_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (artifact_id, version_number)
        )
        """
    )
    for version in versions:
        connection.exec_driver_sql(
            """
            INSERT INTO evidence_versions(
                id, artifact_id, project_id, version_number, relative_path, sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            version,
        )
    op.execute(
        "CREATE INDEX idx_evidence_versions_artifact ON evidence_versions(artifact_id)"
    )
    op.execute(
        """
        CREATE TRIGGER evidence_versions_cannot_change
        BEFORE UPDATE ON evidence_versions
        BEGIN
            SELECT RAISE(ABORT, 'Evidence versions are immutable');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER evidence_versions_cannot_delete
        BEFORE DELETE ON evidence_versions
        BEGIN
            SELECT RAISE(ABORT, 'Evidence versions are immutable');
        END
        """
    )
    op.execute(
        "ALTER TABLE evidence_mappings "
        "ADD COLUMN review_state TEXT NOT NULL DEFAULT 'Not reviewed'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE evidence_mappings DROP COLUMN review_state")
    op.execute("DROP TRIGGER evidence_versions_cannot_delete")
    op.execute("DROP TRIGGER evidence_versions_cannot_change")
    op.execute("DROP INDEX idx_evidence_versions_artifact")
    op.execute("DROP TABLE evidence_versions")
