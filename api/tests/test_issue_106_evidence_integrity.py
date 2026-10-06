"""Evidence hash verification at issuance and selected-evidence export (Issue #106)."""

import io
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.evidence_integrity import _verify_row
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app, _backup
from api.tests.test_issue_m3_hipaa_review import _package, _transition
from api.tests.test_workspace_api import mapping_path


def _with_evidence(client: TestClient, db: Path, suffix: str) -> tuple[str, dict[str, Any], str]:
    project, assessment = _ready(client, db, suffix)
    artifact = client.post(
        f"/api/projects/{project}/evidence",
        files={"file": ("policy.txt", b"synthetic access policy", "text/plain")},
    ).json()
    mapped = client.post(
        mapping_path(project, assessment),
        json={
            "artifact_id": artifact["id"],
            "record_id": "164.308(a)(1)(ii)(A)",
            "rationale": "Synthetic policy evidence.",
        },
    )
    assert mapped.status_code == 201, mapped.text
    package = _package(client, project, assessment)
    for state in ("In Review", "Reviewed", "Ready to issue"):
        assert _transition(client, project, package["id"], state).status_code == 201
    with sqlite3.connect(db) as connection:
        version_id, relative = connection.execute(
            "SELECT id, relative_path FROM evidence_versions WHERE artifact_id=?",
            (artifact["id"],),
        ).fetchone()
    return project, package, version_id + "|" + relative


def _readiness(client: TestClient, project: str, package: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/packages/{package}/issue-readiness")
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def test_verified_evidence_is_indexed_and_issued_manifest_carries_it(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, package, _ = _with_evidence(client, db, "verified")
        readiness = _readiness(client, project, package["id"])
        assert [item["result"] for item in readiness["evidence_index"]] == ["verified"]
        backup = _backup(client, project, package["id"])
        assert backup.status_code == 201, backup.text
        issued = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": backup.json()["id"]},
        )
        assert issued.status_code == 201, issued.text
    with sqlite3.connect(db) as connection:
        manifest = json.loads(
            connection.execute("SELECT manifest_json FROM issuance_snapshots").fetchone()[0]
        )
    assert manifest["evidence_index"][0]["result"] == "verified"


def test_tampered_or_missing_evidence_blocks_backup_and_issue(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, package, identity = _with_evidence(client, db, "tampered")
        relative = identity.split("|")[1]
        (files / relative).write_bytes(b"changed after upload")
        readiness = _readiness(client, project, package["id"])
        assert readiness["pre_backup_issue_ready"] is False
        assert any("failed verification: mismatch" in b for b in readiness["blockers"])
        assert _backup(client, project, package["id"]).status_code == 409
        (files / relative).unlink()
        readiness = _readiness(client, project, package["id"])
        assert any("failed verification: missing" in b for b in readiness["blockers"])


def test_unhashed_version_is_reported() -> None:
    row = {
        "id": "v",
        "artifact_id": "a",
        "artifact_name": "x.txt",
        "version_number": 1,
        "sha256": "",
        "relative_path": "x.txt",
    }
    assert _verify_row(row, Path("/nonexistent"))["result"] == "unhashed"  # type: ignore[arg-type]


def test_selected_evidence_export_is_complete_or_nothing(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, _, identity = _with_evidence(client, db, "export")
        other, _, _ = _with_evidence(client, db, "export-other")
        version_id, relative = identity.split("|")
        exported = client.post(
            f"/api/projects/{project}/evidence-exports",
            json={"evidence_version_ids": [version_id]},
        )
        assert exported.status_code == 200, exported.text
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            index = json.loads(archive.read("evidence-index.json"))
            assert [item["result"] for item in index["items"]] == ["verified"]
            assert archive.read(index["items"][0]["path"]) == b"synthetic access policy"
        assert (
            client.post(
                f"/api/projects/{other}/evidence-exports",
                json={"evidence_version_ids": [version_id]},
            ).status_code
            == 404
        )
        (files / relative).write_bytes(b"tampered")
        failed = client.post(
            f"/api/projects/{project}/evidence-exports",
            json={"evidence_version_ids": [version_id]},
        )
        assert failed.status_code == 409
        assert "mismatch" in failed.json()["detail"]
