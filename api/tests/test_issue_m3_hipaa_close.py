import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app


def project(client: TestClient, name: str) -> str:
    cid = client.post("/api/clients", json={"name": name}).json()["id"]
    return client.post(f"/api/clients/{cid}/projects", json={"name": name}).json()["id"]


def close(client: TestClient, project_id: str):
    return client.get(f"/api/projects/{project_id}/close-readiness/fieldwork_ready_for_generation")


def test_unknown_profile_and_incomplete_profile_are_blockers(tmp_path: Path) -> None:
    with TestClient(create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")) as client:
        pid = project(client, "unknown")
        response = close(client, pid)
        assert response.status_code == 200
        codes = {item["code"] for item in response.json()["blockers"]}
        assert {"profile_not_complete", "profile_not_approved"} <= codes


def test_blank_pending_and_na_without_rationale_are_blockers(tmp_path: Path) -> None:
    with TestClient(create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")) as client:
        pid = project(client, "assessment")
        client.post(f"/api/projects/{pid}/profile-readiness/acknowledgement")
        client.post(f"/api/projects/{pid}/profile-readiness/transitions", json={"next_state":"Intake complete", "decision_note":"test"})
        assessment = client.post(f"/api/projects/{pid}/assessments").json()
        body = close(client, pid).json()
        assert any(item["code"] == "determination_not_final" for item in body["blockers"])
        # The endpoint must not treat a missing/blank determination as complete.
        assert body["ready"] is False
        assert assessment["project_id"] == pid


def test_unknown_target_and_guessed_project_ids_are_rejected(tmp_path: Path) -> None:
    with TestClient(create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")) as client:
        pid = project(client, "one")
        assert close(client, "does-not-exist").status_code == 404
        assert client.get(f"/api/projects/{pid}/close-readiness/not-a-target").status_code == 422


def test_close_readiness_is_project_isolated(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as client:
        one = project(client, "one")
        two = project(client, "two")
        first = close(client, one).json()
        second = close(client, two).json()
        assert first["ready"] is False and second["ready"] is False
        assert first["blockers"] == second["blockers"]
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT id FROM projects").fetchall()
        assert len(rows) == 2


def test_close_readiness_consumes_framework_declaration(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as client:
        pid = project(client, "altered")
        with sqlite3.connect(db) as connection:
            row = connection.execute("SELECT declarations_json, framework_version_id FROM projects WHERE id=?", (pid,)).fetchone()
            declarations = json.loads(connection.execute("SELECT declarations_json FROM framework_versions WHERE id=?", (row[1],)).fetchone()[0])
            declarations["profile_readiness"]["profile_completion"]["state"] = "Synthetic complete"
            connection.execute("UPDATE framework_versions SET declarations_json=? WHERE id=?", (json.dumps(declarations), row[1]))
            connection.commit()
        result = close(client, pid).json()
        assert any(item["code"] == "profile_not_complete" for item in result["blockers"])
