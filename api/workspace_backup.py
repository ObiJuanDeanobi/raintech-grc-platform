"""Workspace backups: Back Up Now, automatic daily/weekly sets, and retention (#117).

Every set uses the ``raintech-recovery-set-v1`` format, so ``api.recovery``
restores it all-or-nothing. Daily sets hold the database and application
metadata; weekly and manual sets also hold managed files and templates.
Pre-issuance backups live in ``backup_records`` and are never touched here.
"""

import contextlib
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from api.issuance import (
    _canonical,
    _file_hash,
    _inventory,
    _inventory_state,
    _operation_lock,
    _validate_archive,
)

RETENTION = {"daily": 14, "weekly": 2}
KINDS = ("daily", "weekly", "manual")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _last(connection: sqlite3.Connection, kind: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = connection.execute(
        """SELECT * FROM workspace_backups WHERE kind = ? AND status IN ('complete', 'pruned')
           ORDER BY started_at DESC LIMIT 1""",
        (kind,),
    ).fetchone()
    return row


def _last_change(connection: sqlite3.Connection) -> str | None:
    row = connection.execute("SELECT MAX(created_at) FROM audit_events").fetchone()
    return row[0] if row else None


def create_backup(
    connection: sqlite3.Connection,
    database_path: Path,
    managed_root: Path,
    template_root: Path,
    backup_root: Path,
    kind: str,
    actor_id: str = "johnathan",
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"Unknown backup kind: {kind}")
    backup_id, started = str(uuid4()), _now()
    target_dir = backup_root / "workspace"
    final_archive = target_dir / f"{kind}-{started[:10]}-{backup_id[:8]}.zip"
    staging: Path | None = None
    with _operation_lock:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix="w-", dir=target_dir))
            staged_archive = staging / "set.zip"
            inventory = [] if kind == "daily" else _inventory(managed_root, template_root)
            before = _inventory_state(inventory)
            estimate = database_path.stat().st_size + sum(p.stat().st_size for *_, p in inventory)
            if shutil.disk_usage(target_dir).free < estimate * 2 + 1024 * 1024:
                raise OSError("Insufficient free space for a workspace backup")
            database_copy = staging / "workspace.db"
            with sqlite3.connect(database_path) as source, sqlite3.connect(database_copy) as copy:
                source.backup(copy)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("SQLite backup integrity check failed")
                version = copy.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            metadata = _canonical(
                {
                    "application": "raintech-grc-platform",
                    "application_version": "0.1.0",
                    "schema_version": version,
                    "secrets_included": False,
                }
            ).encode()
            items = [
                {
                    "path": name,
                    "source_kind": k,
                    **{f: before[name][f] for f in ("sha256", "bytes")},
                }
                for k, name, _ in inventory
            ]
            items.append(
                {
                    "path": "workspace.db",
                    "source_kind": "database",
                    "sha256": _file_hash(database_copy),
                    "bytes": database_copy.stat().st_size,
                }
            )
            items.append(
                {
                    "path": "application.json",
                    "source_kind": "metadata",
                    "sha256": sha256(metadata).hexdigest(),
                    "bytes": len(metadata),
                }
            )
            if inventory and before != _inventory_state(_inventory(managed_root, template_root)):
                raise ValueError("Managed files or templates changed during backup")
            manifest = {
                "schema": "raintech-recovery-set-v1",
                "created_at": started,
                "backup_kind": kind,
                "items": sorted(items, key=lambda item: item["path"]),
            }
            manifest_json = _canonical(manifest)
            manifest_hash = sha256(manifest_json.encode()).hexdigest()
            with zipfile.ZipFile(staged_archive, "w", zipfile.ZIP_DEFLATED) as archive:
                for _, name, source_path in inventory:
                    archive.write(source_path, name)
                archive.write(database_copy, "workspace.db")
                archive.writestr("application.json", metadata)
                archive.writestr("manifest.json", manifest_json.encode())
            _validate_archive(staged_archive, manifest, manifest_hash)
            archive_hash = _file_hash(staged_archive)
            staged_archive.replace(final_archive)
            completed = _now()
            connection.execute(
                """INSERT INTO workspace_backups(
                       id, kind, status, relative_path, manifest_sha256, archive_sha256, bytes,
                       actor_id, started_at, completed_at, failure
                   ) VALUES (?, ?, 'complete', ?, ?, ?, ?, ?, ?, ?, '')""",
                (
                    backup_id,
                    kind,
                    final_archive.relative_to(backup_root).as_posix(),
                    manifest_hash,
                    archive_hash,
                    final_archive.stat().st_size,
                    actor_id,
                    started,
                    completed,
                ),
            )
            connection.commit()
            prune(connection, backup_root)
            return {"id": backup_id, "kind": kind, "status": "complete", "completed_at": completed}
        except Exception as exc:
            # The destination itself may be what failed.
            with contextlib.suppress(OSError):
                final_archive.unlink(missing_ok=True)
            connection.execute(
                """INSERT INTO workspace_backups(
                       id, kind, status, relative_path, manifest_sha256, archive_sha256, bytes,
                       actor_id, started_at, completed_at, failure
                   ) VALUES (?, ?, 'failed', NULL, NULL, NULL, NULL, ?, ?, ?, ?)""",
                (backup_id, kind, actor_id, started, _now(), str(exc) or type(exc).__name__),
            )
            connection.commit()
            return {"id": backup_id, "kind": kind, "status": "failed", "failure": str(exc)}
        finally:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)


def prune(connection: sqlite3.Connection, backup_root: Path) -> list[str]:
    """Delete the oldest automatic sets beyond retention; keep their records."""
    removed: list[str] = []
    for kind, keep in RETENTION.items():
        rows = connection.execute(
            """SELECT id, relative_path FROM workspace_backups
               WHERE kind = ? AND status = 'complete' ORDER BY started_at DESC""",
            (kind,),
        ).fetchall()
        for row in rows[keep:]:
            (backup_root / row["relative_path"]).unlink(missing_ok=True)
            connection.execute(
                "UPDATE workspace_backups SET status = 'pruned' WHERE id = ?", (row["id"],)
            )
            removed.append(row["id"])
    connection.commit()
    return removed


def due(connection: sqlite3.Connection, now: datetime | None = None) -> list[str]:
    """Return the automatic backup kinds that are due, daily before weekly."""
    current = now or datetime.now(UTC)
    change = _last_change(connection)
    if change is None:
        return []
    result = []
    daily = _last(connection, "daily")
    if daily is None or (
        change > daily["started_at"] and daily["started_at"][:10] < current.date().isoformat()
    ):
        result.append("daily")
    weekly = _last(connection, "weekly")
    if weekly is None or (
        change > weekly["started_at"]
        and datetime.fromisoformat(weekly["started_at"]) <= current - timedelta(days=7)
    ):
        result.append("weekly")
    return result


def run_due(
    connection: sqlite3.Connection,
    database_path: Path,
    managed_root: Path,
    template_root: Path,
    backup_root: Path,
) -> list[dict[str, Any]]:
    return [
        create_backup(connection, database_path, managed_root, template_root, backup_root, kind)
        for kind in due(connection)
    ]


def status(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in connection.execute(
            """SELECT id, kind, status, relative_path, archive_sha256, bytes, started_at,
                      completed_at, failure
               FROM workspace_backups ORDER BY started_at DESC LIMIT 50"""
        )
    ]
    warning = None
    for kind in ("daily", "weekly"):
        latest = next((r for r in rows if r["kind"] == kind), None)
        if latest and latest["status"] == "failed":
            warning = f"The last automatic {kind} backup failed: {latest['failure']}"
            break
    return {"backups": rows, "warning": warning}
