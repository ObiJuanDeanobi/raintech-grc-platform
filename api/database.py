import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from alembic import command
from alembic.config import Config


def profile_snapshot_revision(
    connection: sqlite3.Connection, version_id: str, generation: int
) -> str:
    parts: list[object] = [version_id, generation]
    for query in (
        """
        SELECT id, client_key, item_type, environment_item_id, sort_order
        FROM profile_items WHERE profile_version_id = ? ORDER BY sort_order, id
        """,
        """
        SELECT id, profile_item_id, section, field_key, label, value, source,
               reviewer, last_reviewed_at, sort_order
        FROM profile_field_values WHERE profile_version_id = ? ORDER BY sort_order, id
        """,
        """
        SELECT mappings.id, mappings.artifact_id, mappings.evidence_version_id,
               mappings.target_key, mappings.artifact_name_snapshot,
               mappings.uploaded_file_id_snapshot, mappings.rationale,
               mappings.review_state, mappings.created_at, versions.version_number,
               versions.sha256, versions.relative_path
        FROM evidence_mappings mappings
        JOIN evidence_versions versions ON versions.id = mappings.evidence_version_id
        WHERE mappings.target_type = 'profile' AND mappings.profile_version_id = ?
        ORDER BY mappings.created_at, mappings.id
        """,
    ):
        parts.append([list(row) for row in connection.execute(query, (version_id,))])
    canonical = json.dumps(parts, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(canonical).hexdigest()


def register_profile_revision_function(
    connection: sqlite3.Connection, *, allow_migration_ledger_bootstrap: bool = False
) -> None:
    connection.create_function(
        "profile_snapshot_revision",
        2,
        lambda version_id, generation: profile_snapshot_revision(
            connection, str(version_id), int(generation)
        ),
    )
    allowed_ledger_writers = {
        "profile_items_invalidate_revision_insert",
        "profile_items_invalidate_revision_update",
        "profile_items_invalidate_revision_delete",
        "profile_field_values_invalidate_revision_insert",
        "profile_field_values_invalidate_revision_update",
        "profile_field_values_invalidate_revision_delete",
        "profile_mapping_invalidate_revision_insert",
        "profile_mapping_invalidate_revision_update",
        "profile_mapping_invalidate_revision_delete",
    }

    def authorize(
        action: int,
        table: str | None,
        _column: str | None,
        _database: str | None,
        source: str | None,
    ) -> int:
        if (
            action == sqlite3.SQLITE_INSERT
            and table == "profile_content_changes"
            and not allow_migration_ledger_bootstrap
            and source not in allowed_ledger_writers
        ):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_authorizer(authorize)


def configure_connection(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    register_profile_revision_function(connection)


class Database:
    def __init__(self, path: Path, managed_storage_root: Path) -> None:
        self.path = path
        self.managed_storage_root = managed_storage_root

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        migrations = Path(__file__).resolve().parents[1] / "migrations"
        config.set_main_option("script_location", str(migrations))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{self.path.as_posix()}")
        config.set_main_option("raintech.managed_storage_root", str(self.managed_storage_root))
        command.upgrade(config, "head")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        configure_connection(connection)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
