"""Consistent local recovery-set backup and immutable HIPAA issuance."""

import json
import shutil
import sqlite3
import tempfile
import threading
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Never, cast
from uuid import uuid4

from fastapi import HTTPException

from api import evidence_library, evidence_lifecycle
from api.close import fieldwork_ready
from api.cmmc import TERMINAL_POAM_STATUSES
from api.correction import (
    PRESENTATION_ONLY,
    correction_for,
    create_correction,
    current_issuance,
    issuance_blockers,
    package_issuance,
    record_supersession,
)
from api.database import active_assessment_by_id
from api.evidence_integrity import evidence_blockers, verify_assessment_evidence
from api.generation import generate_package
from api.package_review import get_review, record_ready_to_issue
from api.storage import FileStorage

_operation_lock = threading.RLock()


class IssueBlocked(Exception):
    """The data is not ready to issue: what must be fixed first, grouped for a person."""

    def __init__(self, groups: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> None:
        super().__init__("Fix these before issuing")
        self.groups = groups
        self.blockers = blockers


class IssueFailed(Exception):
    """An unexpected failure inside the act; the reason is already audited."""

    def __init__(self, message: str, unexpected: bool = False) -> None:
        super().__init__(message)
        self.unexpected = unexpected


def _reason(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text if isinstance(exc, ValueError | LookupError) else f"{type(exc).__name__}: {text}"


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
    active = active_assessment_by_id(connection, row["assessment_id"])
    if active is None or active["project_id"] != project_id:
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
    query = """SELECT * FROM backup_records WHERE project_id=? AND assessment_id=? AND package_id=?
               AND status='complete' AND source_snapshot_id=? AND source_snapshot_sha256=?
               AND package_sha256=? AND review_event_id=?"""
    args: list[Any] = [
        project_id,
        package["assessment_id"],
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
    blockers.extend(issuance_blockers(connection, project_id, package_id))
    evidence_index = verify_assessment_evidence(
        connection, managed_root, project_id, package["assessment_id"]
    )
    blockers.extend(evidence_blockers(evidence_index))
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
        **package_issuance(connection, project_id, package_id),
        "evidence_index": evidence_index,
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
        try:
            backup_root.mkdir(parents=True, exist_ok=True)
            # Keep the staging name short for Windows MAX_PATH compatibility; the
            # published archive still carries the immutable backup identity.
            staging = Path(tempfile.mkdtemp(prefix="b-", dir=backup_root))
        except OSError as exc:
            # A missing or unwritable backup folder is a failed backup, recorded as one.
            _fail_backup(
                connection,
                identity,
                backup_id,
                actor_id,
                started,
                "backup_folder",
                f"The backup folder cannot be used: {exc.strerror or exc}",
            )
        staged_archive, final_archive = (
            backup_root / "backup.tmp",
            backup_root / f"{backup_id}.zip",
        )
        try:
            stage = "consistency_boundary"
            connection.execute("BEGIN IMMEDIATE")
            inventory = _inventory(managed_root, root / "docs/templates/hipaa")
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
            after = _inventory(managed_root, root / "docs/templates/hipaa")
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
            if readiness["blockers"]:
                raise ValueError("Issuance is blocked: " + "; ".join(readiness["blockers"]))
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
            "evidence_index": readiness["evidence_index"],
        }
        correction = correction_for(connection, project_id, package_id)
        if correction is not None:
            manifest["correction"] = dict(correction)
        reopening = connection.execute(
            "SELECT * FROM assessment_reopenings WHERE successor_assessment_id=?",
            (package["assessment_id"],),
        ).fetchone()
        if reopening is not None:
            manifest["reopening"] = dict(reopening)
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
        record_supersession(connection, project_id, package_id, actor_id)
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


Audit = Callable[[str, str, str, dict[str, Any]], None]

# A second issue of the same assessment inside this window is almost certainly a
# double click or a retry after a timeout, so it is refused (tests set it to 0).
DOUBLE_SUBMIT_SECONDS = 60


def issue_checklist(
    connection: sqlite3.Connection, project_id: str, assessment_id: str, managed_root: Path
) -> dict[str, Any]:
    """What the review-and-issue dialog shows (GitHub issue #145), read-only.

    ``groups`` are the hard gates, each of which stops the issue. ``warnings`` are
    things worth a look that never stop it; nothing needs ticking.
    """
    decision = fieldwork_ready(connection, project_id, assessment_id, storage_root=managed_root)
    framework = connection.execute(
        """SELECT declarations_json FROM framework_versions
           WHERE id = (SELECT framework_version_id FROM projects WHERE id=?)""",
        (project_id,),
    ).fetchone()
    close_validators = (
        json.loads(framework["declarations_json"])
        .get("close_readiness", {})
        .get("fieldwork_ready_for_generation", {})
        .get("validators", [])
    )
    warnings: list[dict[str, Any]] = []
    if "poam_closed" not in close_validators:
        open_actions = connection.execute(
            """SELECT COUNT(*) FROM corrective_actions
               WHERE project_id=? AND status NOT IN ({})""".format(
                ", ".join("?" for _ in TERMINAL_POAM_STATUSES)
            ),
            (project_id, *TERMINAL_POAM_STATUSES),
        ).fetchone()[0]
        if open_actions:
            warnings.append(
                {
                    "key": "open_corrective_work",
                    "label": "Corrective work still open",
                    "count": open_actions,
                    "detail": "It will be listed as open in the POA&M. Issuing does not close it.",
                    "target": "poam",
                }
            )
    library = evidence_library.library(connection, project_id)
    for status, key, label, detail in (
        (
            evidence_lifecycle.STALE,
            "evidence_past_review",
            "Evidence past its review date",
            "A Met that relies on it no longer counts as verified.",
        ),
        (
            evidence_lifecycle.DUE_SOON,
            "evidence_due_soon",
            "Evidence due for review soon",
            "Worth refreshing before the report goes out.",
        ),
    ):
        count = sum(
            1
            for artifact in library["artifacts"]
            if artifact["review_status"] == status and artifact["used_by"]
        )
        if count:
            warnings.append(
                {"key": key, "label": label, "count": count, "detail": detail, "target": "evidence"}
            )
    current = current_issuance(connection, project_id)
    return {
        "ready": bool(decision["ready"]),
        "groups": decision["groups"],
        "blockers": decision["blockers"],
        "warnings": warnings,
        "current_issue": (
            {"package_id": current["package_id"], "issued_at": current["issued_at"]}
            if current is not None
            else None
        ),
    }


def review_and_issue(
    connection: sqlite3.Connection,
    storage: FileStorage,
    database_path: Path,
    managed_root: Path,
    root: Path,
    backup_root: Path,
    project_id: str,
    assessment_id: str,
    actor_id: str,
    reviewer_name: str,
    note: str,
    audit: Audit,
    staging_root: Path | None = None,
    correct_package_id: str | None = None,
) -> dict[str, Any]:
    """The one review-and-issue act (GitHub issue #145, ADR 0021).

    Hard gates, then a fresh package from the data as it is now, then one
    sign-off by the reviewer, then the automatic pre-issuance backup, then issue.
    A failed backup stops the act before anything is issued; the last issued
    version stays current. Every failure is audited.

    When the project already has a current issue of this assessment, the new
    package is a presentation-only correction of it, which supersedes it; changed
    data cannot do that and has to go through reopening, as before.
    """
    with _operation_lock:
        stage = "checks"

        def failed(action: str, entity: str, entity_id: str, details: dict[str, Any]) -> None:
            audit(action, entity, entity_id, {"project_id": project_id, "stage": stage, **details})
            connection.commit()

        try:
            decision = fieldwork_ready(
                connection, project_id, assessment_id, storage_root=managed_root
            )
            if decision["status"] != "Ready":
                connection.rollback()
                failed(
                    "package.issue_blocked",
                    "assessment",
                    assessment_id,
                    {"groups": decision["groups"]},
                )
                raise IssueBlocked(decision["groups"], decision["blockers"])
            stage = "package"
            current = current_issuance(connection, project_id)
            if current is not None and current["assessment_id"] == assessment_id:
                age = (
                    datetime.now(UTC) - datetime.fromisoformat(current["issued_at"])
                ).total_seconds()
                if age < DOUBLE_SUBMIT_SECONDS:
                    raise ValueError(
                        "This was just issued a moment ago. Wait a minute before issuing "
                        "again, or reload to see the issued version."
                    )
            reissue_of = correct_package_id or (
                current["package_id"]
                if current is not None and current["assessment_id"] == assessment_id
                else None
            )
            if reissue_of is not None:
                try:
                    created = create_correction(
                        connection,
                        storage,
                        root,
                        project_id,
                        reissue_of,
                        PRESENTATION_ONLY,
                        True,
                        f"Reissued by {reviewer_name.strip()}"
                        + (f": {note.strip()}" if note.strip() else "."),
                        actor_id,
                        staging_root,
                    )
                except ValueError as exc:
                    if "source changed" in str(exc):
                        raise ValueError(
                            "Your data has changed since the last issue. Reopen the "
                            "assessment to issue a new version."
                        ) from exc
                    raise
                package = created["package"]
                audit(
                    "hipaa_presentation_correction_created",
                    "package_correction",
                    created["correction"]["id"],
                    {"project_id": project_id, "prior_package_id": reissue_of},
                )
            else:
                package = generate_package(
                    connection, storage, root, project_id, assessment_id, staging_root
                )
            audit(
                "hipaa_package_generated",
                "generated_package",
                package["id"],
                {
                    "project_id": project_id,
                    "assessment_id": assessment_id,
                    "source_snapshot_sha256": package["manifest"]["source_snapshot_sha256"],
                },
            )
            connection.commit()
            stage = "review"
            record_ready_to_issue(
                connection,
                project_id,
                package["id"],
                actor_id,
                reviewer_name,
                note,
                root,
                managed_root,
            )
            audit(
                "hipaa_package_review_transition",
                "generated_package",
                package["id"],
                {"project_id": project_id, "next_state": "Ready to issue"},
            )
            connection.commit()
        except IssueBlocked:
            raise
        except Exception as exc:
            if stage == "package":
                # Keep the failed generation attempt the generator recorded.
                connection.commit()
            else:
                connection.rollback()
            failed("package.issue_failed", "assessment", assessment_id, {"reason": _reason(exc)})
            if isinstance(exc, ValueError | LookupError | HTTPException):
                raise
            raise IssueFailed(f"Nothing was issued. {_reason(exc)}", unexpected=True) from exc
        stage = "backup"
        try:
            backup = create_backup(
                connection,
                database_path,
                managed_root,
                root,
                backup_root,
                project_id,
                package["id"],
                actor_id,
            )
        except BackupFailure as exc:
            details = {
                "package_id": package["id"],
                "failed_stage": exc.record["failed_stage"],
                "reason": str(exc),
            }
            audit(
                "hipaa_preissuance_backup_failed",
                "backup_record",
                exc.record["id"],
                {"project_id": project_id, "stage": stage, **details},
            )
            audit(
                "package.backup_failed",
                "backup_record",
                exc.record["id"],
                {"project_id": project_id, "stage": stage, **details},
            )
            failed("package.issue_failed", "generated_package", package["id"], details)
            raise
        audit(
            "hipaa_preissuance_backup_completed",
            "backup_record",
            backup["id"],
            {
                "project_id": project_id,
                "package_id": package["id"],
                "manifest_sha256": backup["manifest_sha256"],
            },
        )
        connection.commit()
        stage = "issue"
        try:
            issued = issue_package(
                connection,
                project_id,
                package["id"],
                backup["id"],
                actor_id,
                root,
                managed_root,
                backup_root,
            )
        except (ValueError, LookupError, sqlite3.Error) as exc:
            connection.rollback()
            reason = _reason(exc)
            audit(
                "hipaa_package_issue_failed",
                "generated_package",
                package["id"],
                {
                    "project_id": project_id,
                    "stage": stage,
                    "backup_id": backup["id"],
                    "reason": reason,
                },
            )
            failed(
                "package.issue_failed",
                "generated_package",
                package["id"],
                {"backup_id": backup["id"], "reason": reason},
            )
            if isinstance(exc, ValueError):
                raise
            raise ValueError(
                f"Nothing was issued. The workspace could not finish the issue ({reason}). "
                "Try again in a moment."
            ) from exc
        superseded = issued["correction"]["prior_package_id"] if issued["correction"] else None
        audit(
            "hipaa_package_issued",
            "issuance_snapshot",
            issued["issued_snapshot_id"],
            {
                "project_id": project_id,
                "package_id": package["id"],
                "backup_id": backup["id"],
                "superseded_package_id": superseded,
            },
        )
        return {
            **issued,
            "reviewer": reviewer_name.strip(),
            "note": note.strip(),
            "backup_id": backup["id"],
            "superseded_package_id": superseded,
        }
