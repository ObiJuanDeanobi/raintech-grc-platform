"""Contract tests for the full-backup and HIPAA issue gate (Issue #73)."""

import hashlib
import sqlite3
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_review import _package, _transition


def _app(tmp_path: Path) -> tuple[TestClient, Path, Path]:
    db = tmp_path / "db.sqlite"
    files = tmp_path / "files"
    return (
        TestClient(create_app(database_path=db, storage_path=files, backup_path=files / "backups")),
        db,
        files,
    )


def _issued_candidate(
    client: TestClient, db: Path, suffix: str = "issue"
) -> tuple[str, str, dict[str, Any]]:
    project, assessment = _ready(client, db, suffix)
    package = _package(client, project, assessment)
    for state in ("In Review", "Reviewed", "Ready to issue"):
        assert _transition(client, project, package["id"], state).status_code == 201
    return project, assessment, package


def _backup(client: TestClient, project: str, package: str, actor: str = "johnathan") -> Response:
    return client.post(
        f"/api/projects/{project}/packages/{package}/backups", json={"actor_id": actor}
    )


def test_issue_readiness_requires_successful_preissuance_backup(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, package = _issued_candidate(client, db, "backup-gate")
        readiness = client.get(f"/api/projects/{project}/packages/{package['id']}/issue-readiness")
        assert readiness.status_code == 200
        assert readiness.json()["ready"] is False
        assert readiness.json()["pre_backup_issue_ready"] is True
        assert readiness.json()["next_action"] == "create_backup"
        backup = _backup(client, project, package["id"])
        assert backup.status_code in (200, 201), backup.text
        backup_id = backup.json()["id"]
        readiness = client.get(f"/api/projects/{project}/packages/{package['id']}/issue-readiness")
        assert readiness.json()["ready"] is True
        issued = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": backup_id},
        )
        assert issued.status_code in (200, 201), issued.text


def test_full_backup_contains_db_managed_files_and_hash_manifest(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, _, package = _issued_candidate(client, db, "backup-archive")
        backup = _backup(client, project, package["id"])
        assert backup.status_code in (200, 201), backup.text
        record = backup.json()
        path = files / "backups" / record.get("relative_path", record.get("path", ""))
        assert path.is_file()
        with ZipFile(path) as archive:
            names = archive.namelist()
            assert names
            assert not any(
                name.startswith(".staging/") or ".." in Path(name).parts for name in names
            )
            assert any(name.endswith(".sqlite") or name.endswith(".db") for name in names)
            manifest_name = next(name for name in names if "manifest" in name.lower())
            manifest = archive.read(manifest_name)
            assert package["id"].encode() in manifest
            for name in names:
                if name != manifest_name:
                    assert hashlib.sha256(archive.read(name)).hexdigest().encode() in manifest
        with sqlite3.connect(db) as connection:
            items = connection.execute(
                "SELECT relative_path, sha256, byte_count FROM backup_items WHERE backup_id=?",
                (record["id"],),
            ).fetchall()
            assert items
            assert {item[0] for item in items} == {
                entry["path"] for entry in record["manifest"]["items"]
            }
            for name, digest, size in items:
                payload = ZipFile(path).read(name)
                assert hashlib.sha256(payload).hexdigest() == digest
                assert len(payload) == size


def test_failed_backup_is_attributed_and_cannot_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as backup_module

    client, db, _ = _app(tmp_path)
    with client:
        project, _, package = _issued_candidate(client, db, "backup-failure")
        monkeypatch.setattr(
            backup_module,
            "_validate_archive",
            lambda *a, **k: (_ for _ in ()).throw(OSError("forced backup failure")),
        )
        response = _backup(client, project, package["id"])
        assert response.status_code >= 400
        assert (
            client.post(
                f"/api/projects/{project}/packages/{package['id']}/issue",
                json={"actor_id": "johnathan", "backup_id": response.json().get("id", "failed")},
            ).status_code
            >= 400
        )
    with sqlite3.connect(db) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE action LIKE '%backup%'"
            ).fetchone()[0]
            >= 1
        )


def test_backup_and_issue_are_project_scoped_and_restart_safe(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, _, package = _issued_candidate(client, db, "backup-one")
        other, _, other_package = _issued_candidate(client, db, "backup-two")
        backup = _backup(client, project, package["id"])
        assert backup.status_code in (200, 201)
        backup_id = backup.json()["id"]
        assert (
            client.get(
                f"/api/projects/{other}/packages/{package['id']}/issue-readiness"
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/projects/{other}/packages/{other_package['id']}/issue",
                json={"actor_id": "johnathan", "backup_id": backup_id},
            ).status_code
            == 409
        )
    with TestClient(create_app(database_path=db, storage_path=files)) as restarted:
        assert (
            restarted.get(
                f"/api/projects/{project}/packages/{package['id']}/issue-readiness"
            ).status_code
            == 200
        )


def test_backup_binding_drift_and_direct_sql_records_are_immutable(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, package = _issued_candidate(client, db, "backup-binding")
        other, _, other_package = _issued_candidate(client, db, "backup-other")
        backup = _backup(client, project, package["id"])
        assert backup.status_code in (200, 201)
        backup_id = backup.json()["id"]
        # A valid backup must not be usable to issue another project's package.
        wrong = client.post(
            f"/api/projects/{other}/packages/{other_package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": backup_id},
        )
        assert wrong.status_code in (404, 409)
        # Changing authoritative source after the backup must invalidate issuance.
        with sqlite3.connect(db) as connection:
            connection.execute(
                "UPDATE determinations SET interview_observation=? WHERE assessment_id=?",
                ("Changed after backup.", assessment),
            )
            connection.commit()
        blocked = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": backup_id},
        )
        assert blocked.status_code in (409, 422)
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT id FROM backup_records WHERE id=?", (backup_id,)
        ).fetchone()
        assert row
        for sql in (
            "UPDATE backup_records SET status='failed' WHERE id=?",
            "DELETE FROM backup_records WHERE id=?",
            "UPDATE backup_items SET sha256='forged' WHERE backup_id=?",
            "DELETE FROM backup_items WHERE backup_id=?",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(sql, (backup_id,))
        # Ownership is enforced by the issuance foreign-key pair/API gate; no
        # project_id column exists on backup_records by design.
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM issuance_snapshots WHERE project_id=?", (other,)
            ).fetchone()[0]
            == 0
        )
