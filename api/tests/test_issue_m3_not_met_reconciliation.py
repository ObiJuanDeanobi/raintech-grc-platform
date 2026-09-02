import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


def workspace(client: TestClient, name: str = "HIPAA") -> tuple[str, str]:
    cid = client.post("/api/clients", json={"name": name}).json()["id"]
    project = client.post(f"/api/clients/{cid}/projects", json={"name": name}).json()
    pid = project["id"]
    client.post(f"/api/projects/{pid}/profile-readiness/acknowledgement")
    client.post(
        f"/api/projects/{pid}/profile-readiness/transitions",
        json={"next_state": "Intake complete", "decision_note": "test"},
    )
    aid = client.post(f"/api/projects/{pid}/assessments").json()["id"]
    return pid, aid


def make_not_met(
    client: TestClient, pid: str, aid: str, record: str = "164.308(a)(1)(ii)(B)"
) -> str:
    response = client.put(
        f"/api/assessments/{aid}/determinations/{record}", json={"status": "Not Met"}
    )
    assert response.status_code == 200, response.text
    return f"/api/projects/{pid}/assessments/{aid}/records/{record}/reconciliation"


def test_create_link_not_needed_and_idempotency(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        pid, aid = workspace(client)
        path = make_not_met(client, pid, aid)
        assert client.get(path).json()["state"] == "unresolved"
        created = client.put(
            path,
            json={
                "outcome": "create",
                "title": "Explicit finding",
                "action_title": "Explicit action",
                "description": "d",
            },
        )
        assert created.status_code == 200
        value = created.json()
        assert value["outcome"] == "create"
        again = client.put(
            path,
            json={
                "outcome": "create",
                "title": "Explicit finding",
                "action_title": "Explicit action",
                "description": "d",
            },
        )
        assert again.json()["id"] == value["id"]
        assert client.put(path, json={"outcome": "not_needed"}).status_code == 422
        skipped = client.put(path, json={"outcome": "not_needed", "rationale": "Risk accepted"})
        assert skipped.status_code == 200
        current = client.get(path).json()
        assert current["state"] == "reconciled"
        assert current["outcome"] == "not_needed"


def test_validation_pending_and_link_isolation(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        pid, aid = workspace(client)
        path = f"/api/projects/{pid}/assessments/{aid}/records/164.308(a)(1)(ii)(B)/reconciliation"
        assert (
            client.put(
                path, json={"outcome": "create", "title": "x", "action_title": "y"}
            ).status_code
            == 422
        )
        assert client.put(path, json={"outcome": "not_needed", "rationale": "x"}).status_code == 422
        other_pid, other_aid = workspace(client, "Other")
        other_path = make_not_met(client, other_pid, other_aid)
        make_not_met(client, pid, aid)
        created = client.put(
            other_path, json={"outcome": "create", "title": "f", "action_title": "a"}
        ).json()
        assert (
            client.put(
                f"/api/projects/{pid}/assessments/{aid}/records/164.308(a)(1)(ii)(B)/reconciliation",
                json={
                    "outcome": "link_existing",
                    "finding_id": created["finding_id"],
                    "corrective_action_id": created["corrective_action_id"],
                },
            ).status_code
            == 422
        )


def test_direct_sql_guards_and_restart_persistence(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    app = create_app(database_path=db, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        pid, aid = workspace(client)
        path = make_not_met(client, pid, aid)
        saved = client.put(
            path, json={"outcome": "create", "title": "F", "action_title": "A"}
        ).json()
    connection = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO not_met_reconciliations(
                id, project_id, assessment_id, record_id, outcome
            ) VALUES ('x', 'wrong', 'a', 'r', 'create')
            """
        )
    with pytest.raises(sqlite3.DatabaseError):
        connection.execute("DELETE FROM not_met_reconciliation_history")
    connection.close()
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as client:
        current = client.get(path).json()
        assert current["state"] == "reconciled"
        assert current["outcome"] == saved["outcome"]
