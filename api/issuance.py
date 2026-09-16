"""Consistent local recovery-set backup and immutable HIPAA issuance."""

import json
import shutil
import sqlite3
import tempfile
import threading
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Never, cast
from uuid import uuid4

from api.close import fieldwork_ready
from api.package_review import get_review

_operation_lock = threading.RLock()


class BackupFailure(RuntimeError):
    def __init__(self, record: dict[str, Any]) -> None:
        super().__init__(record["error"])
        self.record = record


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package(connection: sqlite3.Connection, project_id: str, package_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM generated_packages WHERE id=? AND project_id=?", (package_id, project_id)
    ).fetchone()
    if row is None:
        raise LookupError("Package not found")
    return cast(sqlite3.Row, row)


def _review_event(
    connection: sqlite3.Connection, project_id: str, package_id: str
) -> sqlite3.Row | None:
    row = connection.execute(
        """SELECT * FROM package_review_events
           WHERE project_id=? AND package_id=? AND next_state='Ready to issue'
           ORDER BY sequence DESC LIMIT 1""",
        (project_id, package_id),
    ).fetchone()
    return cast(sqlite3.Row | None, row)


def _inventory(managed_root: Path, template_root: Path) -> list[tuple[str, str, Path]]:
    result: list[tuple[str, str, Path]] = []
    backup_root = (managed_root / "backups").resolve()
    for kind, base in (("managed", managed_root), ("template", template_root)):
        if not base.exists():
            continue
        resolved_base = base.resolve()
        for source in sorted(base.rglob("*"), key=lambda item: item.as_posix()):
            if not source.is_file() or ".staging" in source.parts:
                continue
            resolved = source.resolve()
            if source.is_symlink() or resolved_base not in resolved.parents:
                raise ValueError(f"Unsafe {kind} path: {source}")
            lowered = source.name.lower()
            if (
                lowered == ".env"
                or lowered in {"credentials", "credentials.json", "id_rsa", "id_ed25519"}
                or source.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
            ):
                raise ValueError(
                    f"Secret or machine-authentication file cannot be backed up: {source.name}"
                )
            if kind == "managed" and (resolved == backup_root or backup_root in resolved.parents):
                continue
            result.append((kind, f"{kind}/{source.relative_to(base).as_posix()}", source))
    return result


def _inventory_state(inventory: list[tuple[str, str, Path]]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "sha256": _file_hash(path),
            "bytes": path.stat().st_size,
            "modified_ns": path.stat().st_mtime_ns,
        }
        for _, name, path in inventory
    }


def _validate_archive(path: Path, manifest: dict[str, Any], manifest_hash: str) -> None:
    if sha256(_canonical(manifest).encode()).hexdigest() != manifest_hash:
        raise ValueError("Backup manifest hash mismatch")
    items = {item["path"]: item for item in manifest["items"]}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            name.startswith("/") or ".." in Path(name).parts for name in names
        ):
            raise ValueError("Backup archive contains an unsafe path")
        if set(names) != set(items) | {"manifest.json"}:
            raise ValueError("Backup archive contents do not match its manifest")
        if json.loads(archive.read("manifest.json")) != manifest:
            raise ValueError("Backup archive manifest changed")
        for name, item in items.items():
            content = archive.read(name)
            if len(content) != item["bytes"] or sha256(content).hexdigest() != item["sha256"]:
                raise ValueError(f"Backup item validation failed: {name}")


def _valid_backup(
    connection: sqlite3.Connection,
    project_id: str,
    package: sqlite3.Row,
    event: sqlite3.Row | None,
    backup_root: Path,
    backup_id: str | None,
) -> sqlite3.Row | None:
    if event is None:
        return None
    source_hash = connection.execute(
        "SELECT sha256 FROM source_snapshots WHERE id=? AND project_id=?",
        (package["source_snapshot_id"], project_id),
    ).fetchone()[0]
    query = """SELECT * FROM backup_records WHERE project_id=? AND package_id=?
               AND status='complete' AND source_snapshot_id=? AND source_snapshot_sha256=?
               AND package_sha256=? AND review_event_id=?"""
    args: list[Any] = [
        project_id,
        package["id"],
        package["source_snapshot_id"],
        source_hash,
        package["sha256"],
        event["id"],
    ]
    if backup_id is not None:
        query += " AND id=?"
        args.append(backup_id)
    backup = connection.execute(query + " ORDER BY completed_at DESC LIMIT 1", args).fetchone()
    if backup is None:
        return None
    archive = (backup_root / backup["relative_path"]).resolve()
    if backup_root.resolve() not in archive.parents or not archive.is_file():
        return None
    try:
        if _file_hash(archive) != backup["archive_sha256"]:
            return None
        _validate_archive(archive, json.loads(backup["manifest_json"]), backup["manifest_sha256"])
    except (ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
        return None
    return cast(sqlite3.Row, backup)


def issue_readiness(
    connection: sqlite3.Connection,
    project_id: str,
    package_id: str,
    root: Path,
    managed_root: Path,
    backup_root: Path,
    backup_id: str | None = None,
) -> dict[str, Any]:
    package = _package(connection, project_id, package_id)
    review = get_review(connection, project_id, package_id, root, managed_root)
    event = _review_event(connection, project_id, package_id)
    blockers = list(review["blockers"]) + list(review["drift"])
    if review["state"] != "Ready to issue" or event is None:
        blockers.append("The exact package has not been reviewed and signed off")
    if fieldwork_ready(connection, project_id, package["assessment_id"]).get("status") != "Ready":
        blockers.append("Assessment source is no longer ready")
    backup = _valid_backup(connection, project_id, package, event, backup_root, backup_id)
    issued = connection.execute(
        "SELECT * FROM issuance_snapshots WHERE project_id=? AND package_id=?",
        (project_id, package_id),
    ).fetchone()
    pre_ready = not blockers and issued is None
    final_ready = pre_ready and backup is not None
    failure = connection.execute(
        """SELECT * FROM backup_records WHERE project_id=? AND package_id=? AND status='failed'
           ORDER BY completed_at DESC LIMIT 1""",
        (project_id, package_id),
    ).fetchone()
    return {
        "target": "final_issue_ready" if backup else "pre_backup_issue_ready",
        "status": "Issued" if issued else ("Ready" if pre_ready else "Blocked"),
        "ready": final_ready,
        "pre_backup_issue_ready": pre_ready,
        "final_issue_ready": final_ready,
        "blockers": blockers,
        "checks": [
            {"key": "exact_review", "status": "pass" if event else "fail"},
            {"key": "current_source_and_files", "status": "pass" if not blockers else "fail"},
            {"key": "exact_backup", "status": "pass" if backup else "next_action"},
        ],
        "next_action": "create_backup" if pre_ready and backup is None else None,
        "package_id": package_id,
        "source_snapshot_id": package["source_snapshot_id"],
        "source_sha256": review["binding"]["source_snapshot_sha256"],
        "manifest_sha256": package["sha256"],
        "backup_id": backup["id"] if backup else None,
        "backup_manifest_sha256": backup["manifest_sha256"] if backup else None,
        "backup_completed_at": backup["completed_at"] if backup else None,
        "issued_snapshot_id": issued["id"] if issued else None,
        "issued_at": issued["issued_at"] if issued else None,
        "failure": (
            {
                "attempt_id": failure["id"],
                "stage": failure["failed_stage"],
                "reason": failure["error"],
            }
            if failure
            else None
        ),
    }


def _fail_backup(
    connection: sqlite3.Connection,
    identity: dict[str, Any],
    backup_id: str,
    actor_id: str,
    started: str,
    stage: str,
    error: str,
) -> Never:
    connection.execute(
        """INSERT INTO backup_records(
          id,project_id,assessment_id,package_id,source_snapshot_id,source_snapshot_sha256,
          package_sha256,review_event_id,actor_id,status,relative_path,manifest_json,
          manifest_sha256,archive_sha256,byte_count,started_at,completed_at,failed_stage,error)
          VALUES (?,?,?,?,?,?,?,?,?,'failed','','{}','','',0,?,?,?,?)""",
        (
            backup_id,
            identity["project_id"],
            identity["assessment_id"],
            identity["package_id"],
            identity["source_snapshot_id"],
            identity["source_snapshot_sha256"],
            identity["package_sha256"],
            identity["review_event_id"],
            actor_id,
            started,
            _now(),
            stage,
            error[:4000],
        ),
    )
    record = dict(
        connection.execute("SELECT * FROM backup_records WHERE id=?", (backup_id,)).fetchone()
    )
    raise BackupFailure(record)


def create_backup(
    connection: sqlite3.Connection,
    database_path: Path,
    managed_root: Path,
    root: Path,
    backup_root: Path,
    project_id: str,
    package_id: str,
    actor_id: str,
) -> dict[str, Any]:
    package = _package(connection, project_id, package_id)
    review = get_review(connection, project_id, package_id, root, managed_root)
    event = _review_event(connection, project_id, package_id)
    identity = {
        "project_id": project_id,
        "assessment_id": package["assessment_id"],
        "package_id": package_id,
        "source_snapshot_id": package["source_snapshot_id"],
        "source_snapshot_sha256": review["binding"]["source_snapshot_sha256"],
        "package_sha256": package["sha256"],
        "review_event_id": event["id"] if event else None,
    }
    backup_id, started, stage = str(uuid4()), _now(), "preconditions"
    with _operation_lock:
        readiness = issue_readiness(
            connection, project_id, package_id, root, managed_root, backup_root
        )
        if not readiness["pre_backup_issue_ready"]:
            _fail_backup(
                connection,
                identity,
                backup_id,
                actor_id,
                started,
                stage,
                "; ".join(readiness["blockers"]),
            )
        backup_root.mkdir(parents=True, exist_ok=True)
        # Keep the staging name short for Windows MAX_PATH compatibility; the
        # published archive still carries the immutable backup identity.
        staging = Path(tempfile.mkdtemp(prefix="b-", dir=backup_root))
        staged_archive, final_archive = (
            backup_root / "backup.tmp",
            backup_root / f"{backup_id}.zip",
        )
        try:
            stage = "consistency_boundary"
            connection.execute("BEGIN IMMEDIATE")
            inventory = _inventory(managed_root, root / "docs/templates/hipaa/v2")
            before = _inventory_state(inventory)
            estimate = database_path.stat().st_size + sum(
                path.stat().st_size for _, _, path in inventory
            )
            if shutil.disk_usage(backup_root).free < estimate * 2 + 1024 * 1024:
                raise OSError("Insufficient free space for recovery set")
            stage = "database"
            database_copy = staging / "workspace.db"
            with (
                sqlite3.connect(database_path) as database_source,
                sqlite3.connect(database_copy) as target,
            ):
                database_source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("SQLite backup integrity check failed")
            stage = "files"
            items: list[dict[str, Any]] = [
                {
                    "path": name,
                    "source_kind": kind,
                    "sha256": before[name]["sha256"],
                    "bytes": before[name]["bytes"],
                }
                for kind, name, _ in inventory
            ]
            items.append(
                {
                    "path": "workspace.db",
                    "source_kind": "database",
                    "sha256": _file_hash(database_copy),
                    "bytes": database_copy.stat().st_size,
                }
            )
            version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            metadata_bytes = _canonical(
                {
                    "application": "raintech-grc-platform",
                    "application_version": "0.1.0",
                    "schema_version": version,
                    "secrets_included": False,
                }
            ).encode()
            items.append(
                {
                    "path": "application.json",
                    "source_kind": "metadata",
                    "sha256": sha256(metadata_bytes).hexdigest(),
                    "bytes": len(metadata_bytes),
                }
            )
            after = _inventory(managed_root, root / "docs/templates/hipaa/v2")
            if before != _inventory_state(after) or [x[1] for x in inventory] != [
                x[1] for x in after
            ]:
                raise ValueError("Managed files or templates changed during backup")
            stage = "manifest"
            manifest = {
                "schema": "raintech-recovery-set-v1",
                "created_at": started,
                **identity,
                "items": sorted(items, key=lambda item: item["path"]),
            }
            manifest_json = _canonical(manifest)
            manifest_hash = sha256(manifest_json.encode()).hexdigest()
            stage = "archive"
            with zipfile.ZipFile(staged_archive, "w", zipfile.ZIP_DEFLATED) as archive:
                for _, name, source in inventory:
                    archive.write(source, name)
                archive.write(database_copy, "workspace.db")
                archive.writestr("application.json", metadata_bytes)
                archive.writestr("manifest.json", manifest_json.encode())
            _validate_archive(staged_archive, manifest, manifest_hash)
            archive_hash = _file_hash(staged_archive)
            staged_archive.replace(final_archive)
            completed = _now()
            connection.execute(
                """INSERT INTO backup_records VALUES
                (?,?,?,?,?,?,?,?,?,'complete',?,?,?,?,?,?,?,NULL,'')""",
                (
                    backup_id,
                    project_id,
                    package["assessment_id"],
                    package_id,
                    package["source_snapshot_id"],
                    identity["source_snapshot_sha256"],
                    package["sha256"],
                    identity["review_event_id"],
                    actor_id,
                    final_archive.name,
                    manifest_json,
                    manifest_hash,
                    archive_hash,
                    final_archive.stat().st_size,
                    started,
                    completed,
                ),
            )
            for item in manifest["items"]:
                connection.execute(
                    "INSERT INTO backup_items VALUES (?,?,?,?,?,?,?)",
                    (
                        str(uuid4()),
                        backup_id,
                        project_id,
                        item["path"],
                        item["source_kind"],
                        item["sha256"],
                        item["bytes"],
                    ),
                )
            return {
                "id": backup_id,
                "status": "complete",
                "relative_path": final_archive.name,
                "sha256": archive_hash,
                "manifest_sha256": manifest_hash,
                "completed_at": completed,
                "manifest": manifest,
            }
        except BackupFailure:
            raise
        except Exception as exc:
            connection.rollback()
            staged_archive.unlink(missing_ok=True)
            final_archive.unlink(missing_ok=True)
            _fail_backup(connection, identity, backup_id, actor_id, started, stage, str(exc))
        finally:
            shutil.rmtree(staging, ignore_errors=True)


def issue_package(
    connection: sqlite3.Connection,
    project_id: str,
    package_id: str,
    backup_id: str,
    actor_id: str,
    root: Path,
    managed_root: Path,
    backup_root: Path,
) -> dict[str, Any]:
    package = _package(connection, project_id, package_id)
    attempt_id, started = str(uuid4()), _now()
    with _operation_lock:
        connection.execute("BEGIN IMMEDIATE")
        readiness = issue_readiness(
            connection, project_id, package_id, root, managed_root, backup_root, backup_id
        )
        if not readiness["final_issue_ready"]:
            valid_backup_id = (
                backup_id
                if connection.execute(
                    "SELECT 1 FROM backup_records WHERE id=? AND project_id=?",
                    (backup_id, project_id),
                ).fetchone()
                else None
            )
            connection.execute(
                "INSERT INTO issuance_attempts VALUES (?,?,?,?,?,?,'failed',?,?,?)",
                (
                    attempt_id,
                    project_id,
                    package["assessment_id"],
                    package_id,
                    valid_backup_id,
                    actor_id,
                    started,
                    _now(),
                    "Exact backup or package binding is invalid",
                ),
            )
            raise ValueError("Issuance is blocked: exact backup or package binding is invalid")
        backup = connection.execute(
            "SELECT * FROM backup_records WHERE id=? AND project_id=?", (backup_id, project_id)
        ).fetchone()
        review = _review_event(connection, project_id, package_id)
        source = connection.execute(
            "SELECT * FROM source_snapshots WHERE id=? AND project_id=?",
            (package["source_snapshot_id"], project_id),
        ).fetchone()
        if backup is None or review is None or source is None:
            raise ValueError("Issuance binding disappeared during the final check")
        backup = cast(sqlite3.Row, backup)
        source = cast(sqlite3.Row, source)
        issued_at, snapshot_id = _now(), str(uuid4())
        manifest = {
            "schema": "raintech-issued-snapshot-v1",
            "project_id": project_id,
            "assessment_id": package["assessment_id"],
            "package": dict(package),
            "source_snapshot": {**dict(source), "source_json": json.loads(source["source_json"])},
            "review_event": dict(review),
            "backup": dict(backup),
            "issued_at": issued_at,
            "issuer_id": actor_id,
        }
        manifest_json = _canonical(manifest)
        connection.execute(
            "INSERT INTO issuance_attempts VALUES (?,?,?,?,?,?,'issued',?,?,?)",
            (
                attempt_id,
                project_id,
                package["assessment_id"],
                package_id,
                backup_id,
                actor_id,
                started,
                issued_at,
                "",
            ),
        )
        connection.execute(
            "INSERT INTO issuance_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                snapshot_id,
                project_id,
                package["assessment_id"],
                package_id,
                attempt_id,
                backup_id,
                package["source_snapshot_id"],
                review["id"],
                package["sha256"],
                source["sha256"],
                backup["manifest_sha256"],
                manifest_json,
                sha256(manifest_json.encode()).hexdigest(),
                actor_id,
                issued_at,
            ),
        )
        return issue_readiness(
            connection, project_id, package_id, root, managed_root, backup_root, backup_id
        )
