import sqlite3
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _backup
from api.tests.test_issue_m3_hipaa_review import _package, _transition


def create_project(client: TestClient, client_id: str, name: str) -> str:
    response = client.post(f"/api/clients/{client_id}/projects", json={"name": name})
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def create_assessment(client: TestClient, project_id: str) -> str:
    assert (
        client.post(
            f"/api/projects/{project_id}/profile-readiness/transitions",
            json={
                "next_state": "Intake complete",
                "decision_note": "Synthetic assessment intake completed.",
            },
        ).status_code
        == 201
    )
    response = client.post(f"/api/projects/{project_id}/assessments")
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def state_counts(database_path: Path, project_id: str) -> tuple[int, int, int, int]:
    with sqlite3.connect(database_path) as connection:
        return cast(
            tuple[int, int, int, int],
            connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM assessments WHERE project_id = ?),
                  (SELECT COUNT(*) FROM assessment_revisions WHERE project_id = ?),
                  (SELECT COUNT(*) FROM project_active_assessments WHERE project_id = ?),
                  (SELECT COUNT(*) FROM audit_events WHERE entity_type = 'assessment'
                    AND entity_id IN (SELECT id FROM assessments WHERE project_id = ?))
                """,
                (project_id, project_id, project_id, project_id),
            ).fetchone(),
        )


def predecessor_history(
    database_path: Path, project_id: str, assessment_id: str, package_id: str
) -> dict[str, list[tuple[object, ...]]]:
    with sqlite3.connect(database_path) as connection:
        queries = {
            "assessment": ("SELECT * FROM assessments WHERE id = ?", (assessment_id,)),
            "revision": (
                "SELECT * FROM assessment_revisions WHERE assessment_id = ?",
                (assessment_id,),
            ),
            "determinations": (
                "SELECT * FROM determinations WHERE assessment_id = ? ORDER BY record_id",
                (assessment_id,),
            ),
            "evidence_mappings": (
                "SELECT * FROM evidence_mappings WHERE assessment_id = ? ORDER BY id",
                (assessment_id,),
            ),
            "source_snapshots": (
                "SELECT * FROM source_snapshots WHERE assessment_id = ? ORDER BY id",
                (assessment_id,),
            ),
            "generated_packages": (
                "SELECT * FROM generated_packages WHERE id = ?",
                (package_id,),
            ),
            "generated_components": (
                "SELECT * FROM generated_components WHERE package_id = ? ORDER BY kind",
                (package_id,),
            ),
            "package_review_events": (
                "SELECT * FROM package_review_events WHERE package_id = ? ORDER BY sequence",
                (package_id,),
            ),
            "backup_records": (
                "SELECT * FROM backup_records WHERE package_id = ? ORDER BY id",
                (package_id,),
            ),
            "backup_items": (
                "SELECT i.* FROM backup_items i JOIN backup_records b ON b.id = i.backup_id "
                "WHERE b.package_id = ? ORDER BY i.relative_path",
                (package_id,),
            ),
            "issuance_attempts": (
                "SELECT * FROM issuance_attempts WHERE package_id = ? ORDER BY id",
                (package_id,),
            ),
            "issuance_snapshots": (
                "SELECT * FROM issuance_snapshots WHERE package_id = ? ORDER BY id",
                (package_id,),
            ),
            "profile_versions": (
                "SELECT * FROM profile_versions WHERE project_id = ? ORDER BY version_number",
                (project_id,),
            ),
            "profile_lifecycle_events": (
                "SELECT e.* FROM profile_lifecycle_events e JOIN profile_versions v "
                "ON v.id = e.profile_version_id WHERE v.project_id = ? ORDER BY e.id",
                (project_id,),
            ),
        }
        return {
            label: connection.execute(sql, parameters).fetchall()
            for label, (sql, parameters) in queries.items()
        }


def test_successor_requires_current_project_predecessor_and_writes_nothing_on_rejection(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_a = client.post("/api/clients", json={"name": "Synthetic Client A"}).json()["id"]
        client_b = client.post("/api/clients", json={"name": "Synthetic Client B"}).json()["id"]
        project_a = create_project(client, client_a, "Synthetic Project A")
        project_b = create_project(client, client_b, "Synthetic Project B")
        predecessor_a = create_assessment(client, project_a)
        predecessor_b = create_assessment(client, project_b)
        before_b = state_counts(database_path, project_b)

        same_client_project = create_project(client, client_a, "Synthetic Project C")
        predecessor_c = create_assessment(client, same_client_project)
        before_c = state_counts(database_path, same_client_project)

        payload = {"actor_id": "johnathan", "reason": "Synthetic successor contract test."}
        advanced = client.post(
            f"/api/projects/{project_a}/assessments/{predecessor_a}/successor", json=payload
        )
        assert advanced.status_code == 201
        before_a = state_counts(database_path, project_a)
        guessed = client.post(
            f"/api/projects/{project_a}/assessments/{predecessor_b}/successor", json=payload
        )
        stale_after_success = client.post(
            f"/api/projects/{project_a}/assessments/{predecessor_a}/successor", json=payload
        )
        guessed_same_client_project = client.post(
            f"/api/projects/{project_a}/assessments/{predecessor_c}/successor", json=payload
        )

        assert guessed.status_code == 404
        assert stale_after_success.status_code == 409
        assert guessed_same_client_project.status_code == 404
        assert state_counts(database_path, project_a) == before_a
        assert state_counts(database_path, project_b) == before_b
        assert state_counts(database_path, same_client_project) == before_c


def test_successor_advances_revision_audit_and_survives_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        client_id = client.post("/api/clients", json={"name": "Synthetic Client"}).json()["id"]
        project_id = create_project(client, client_id, "Synthetic HIPAA Project")
        predecessor = create_assessment(client, project_id)
        response = client.post(
            f"/api/projects/{project_id}/assessments/{predecessor}/successor",
            json={"actor_id": "johnathan", "reason": "Synthetic authorized successor."},
        )
        assert response.status_code == 201
        successor = response.json()
        assert successor["id"] != predecessor
        assert successor["project_id"] == project_id
        assert successor["framework_version_id"] == "hipaa-45cfr164-2026-07-01"
        assert successor["revision_number"] == 2
        assert successor["predecessor_assessment_id"] == predecessor

        active = client.get(f"/api/projects/{project_id}/assessment")
        assert active.status_code == 200
        assert active.json()["id"] == successor["id"]

        assert client.post(f"/api/projects/{project_id}/assessments").status_code == 409

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id = ?",
            (project_id,),
        ).fetchone() == (successor["id"],)
        assert connection.execute(
            """
            SELECT assessment_id, revision_number, predecessor_assessment_id
            FROM assessment_revisions WHERE project_id = ? ORDER BY revision_number
            """,
            (project_id,),
        ).fetchall() == [(predecessor, 1, None), (successor["id"], 2, predecessor)]
        audit = connection.execute(
            """
            SELECT actor_id, action, details_json FROM audit_events
            WHERE entity_type = 'assessment' AND entity_id = ?
            """,
            (successor["id"],),
        ).fetchone()
        assert audit is not None
        assert audit[0] == "johnathan"
        assert audit[1] == "assessment.successor_created"
        assert "Synthetic authorized successor." in audit[2]

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        active = client.get(f"/api/projects/{project_id}/assessment")
        assert active.status_code == 200
        assert active.json()["id"] == successor["id"]


def test_successor_preserves_predecessor_evidence_snapshot_package_signoff_and_issuance(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        # Move the synthetic project through full fieldwork close and exact package review.
        project_id, predecessor = _ready(client, database_path, "successor-immutability")
        uploaded = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("synthetic-evidence.txt", b"synthetic evidence only", "text/plain")},
        )
        assert uploaded.status_code == 201, uploaded.text
        mapped = client.post(
            f"/api/projects/{project_id}/assessments/{predecessor}/evidence-mappings",
            json={
                "artifact_id": uploaded.json()["id"],
                "record_id": "164.308(a)(1)(ii)(A)",
                "rationale": "Synthetic evidence supports the assessment.",
            },
        )
        assert mapped.status_code == 201, mapped.text

        package = _package(client, project_id, predecessor)
        for state in ("In Review", "Reviewed", "Ready to issue"):
            signed = _transition(client, project_id, package["id"], state)
            assert signed.status_code == 201, signed.text
        backup = _backup(client, project_id, package["id"])
        assert backup.status_code in (200, 201), backup.text
        issued = client.post(
            f"/api/projects/{project_id}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": backup.json()["id"]},
        )
        assert issued.status_code in (200, 201), issued.text
        before = predecessor_history(database_path, project_id, predecessor, package["id"])

        successor_response = client.post(
            f"/api/projects/{project_id}/assessments/{predecessor}/successor",
            json={"actor_id": "johnathan", "reason": "Synthetic successor after issued package."},
        )
        assert successor_response.status_code == 201, successor_response.text

        after = predecessor_history(database_path, project_id, predecessor, package["id"])
        assert after == before
        assert before["evidence_mappings"]
        assert before["source_snapshots"]
        assert before["generated_packages"]
        assert before["generated_components"]
        assert len(before["package_review_events"]) == 3
        assert before["backup_records"][0][9] == "complete"
        assert before["issuance_snapshots"]
        assert client.post(f"/api/projects/{project_id}/assessments").status_code == 409


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"actor_id": "johnathan", "reason": "   "}, 422),
        ({"reason": "No actor supplied."}, 422),
        ({"actor_id": "unknown-reviewer", "reason": "Synthetic reason."}, 422),
    ],
)
def test_invalid_successor_decisions_are_rejected_without_writes(
    tmp_path: Path,
    payload: dict[str, str],
    expected_status: int,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_id = client.post("/api/clients", json={"name": "Synthetic Client"}).json()["id"]
        project_id = create_project(client, client_id, "Synthetic Project")
        predecessor = create_assessment(client, project_id)
        before = state_counts(database_path, project_id)
        response = client.post(
            f"/api/projects/{project_id}/assessments/{predecessor}/successor", json=payload
        )
        assert response.status_code == expected_status
        assert state_counts(database_path, project_id) == before
