import sqlite3
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


def create_project(client: TestClient, client_id: str, name: str) -> str:
    response = client.post(
        f"/api/clients/{client_id}/projects",
        json={"name": name},
    )
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def create_assessment(client: TestClient, project_id: str) -> str:
    assert (
        client.post(f"/api/projects/{project_id}/profile-readiness/acknowledgement").status_code
        == 201
    )
    assert (
        client.post(
            f"/api/projects/{project_id}/profile-readiness/transitions",
            json={
                "next_state": "Intake complete",
                "decision_note": "Synthetic test intake completed.",
            },
        ).status_code
        == 201
    )
    response = client.post(f"/api/projects/{project_id}/assessments")
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def active_pointer(database_path: Path, project_id: str) -> str:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    assert row is not None
    return cast(str, row[0])


@pytest.mark.parametrize("same_client", [True, False])
def test_assessment_reads_and_writes_are_isolated_by_active_project(
    tmp_path: Path,
    same_client: bool,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_a = client.post("/api/clients", json={"name": "Client A"}).json()["id"]
        client_b = (
            client_a
            if same_client
            else client.post("/api/clients", json={"name": "Client B"}).json()["id"]
        )
        project_a = create_project(client, client_a, "Project A")
        project_b = create_project(client, client_b, "Project B")
        assessment_a = create_assessment(client, project_a)
        assessment_b = create_assessment(client, project_b)

        assert client.get(f"/api/projects/{project_a}/assessment").json()["id"] == assessment_a
        assert client.get(f"/api/projects/{project_b}/assessment").json()["id"] == assessment_b
        assert client.get(
            f"/api/projects/{project_b}/assessments/{assessment_a}"
            "/records/164.308(a)(1)(ii)(A)"
        ).status_code == 404
        assert client.post(
            f"/api/projects/{project_b}/assessments/{assessment_a}/evidence-mappings",
            json={
                "artifact_id": "guessed-artifact",
                "record_id": "164.308(a)(1)(ii)(A)",
                "rationale": "Must not mutate another project's assessment.",
            },
        ).status_code == 404

        before_a = client.get(
            f"/api/projects/{project_a}/assessments/{assessment_a}"
            "/records/164.308(a)(1)(ii)(A)"
        ).json()
        pointer_a = active_pointer(database_path, project_a)
        pointer_b = active_pointer(database_path, project_b)

        # A valid active ID remains usable on legacy assessment-only routes.
        assert client.put(
            f"/api/assessments/{assessment_a}/records/164.308(a)(1)(ii)(A)/note",
            json={"note": "Must not mutate another or inactive revision."},
        ).status_code == 200
        # A guessed ID that is not the project's active assessment is rejected.
        rejected = client.put(
            "/api/assessments/guessed-assessment/determinations/164.308(a)(1)(ii)(A)",
            json={"status": "Not Met"},
        )
        assert rejected.status_code == 404

        # The legitimate project's state remains readable and pointer identity is stable.
        after_a = client.get(
            f"/api/projects/{project_a}/assessments/{assessment_a}"
            "/records/164.308(a)(1)(ii)(A)"
        ).json()
        assert after_a["note"] == "Must not mutate another or inactive revision."
        assert after_a["determination"] == before_a["determination"]
        assert active_pointer(database_path, project_a) == pointer_a == assessment_a
        assert active_pointer(database_path, project_b) == pointer_b == assessment_b


def test_assessment_creation_still_rejects_second_active_assessment(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_id = client.post("/api/clients", json={"name": "Client"}).json()["id"]
        project_id = create_project(client, client_id, "Project")
        assessment_id = create_assessment(client, project_id)

        assert client.post(f"/api/projects/{project_id}/assessments").status_code == 409
        assert active_pointer(tmp_path / "workspace.db", project_id) == assessment_id


def test_database_rejects_cross_project_active_pointer(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_a = client.post("/api/clients", json={"name": "Client A"}).json()["id"]
        client_b = client.post("/api/clients", json={"name": "Client B"}).json()["id"]
        project_a = create_project(client, client_a, "Project A")
        project_b = create_project(client, client_b, "Project B")
        assessment_a = create_assessment(client, project_a)
        assessment_b = create_assessment(client, project_b)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE project_active_assessments SET assessment_id = ? WHERE project_id = ?",
                (assessment_b, project_a),
            )
        connection.rollback()
        assert connection.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id = ?",
            (project_a,),
        ).fetchone() == (assessment_a,)
