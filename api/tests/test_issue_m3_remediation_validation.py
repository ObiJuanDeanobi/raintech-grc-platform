import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app

RECORD = "164.308(a)(1)(ii)(B)"


def setup_case(
    client: TestClient, name: str = "Validation client"
) -> tuple[str, str, str]:
    cid = client.post("/api/clients", json={"name": name}).json()["id"]
    pid = client.post(f"/api/clients/{cid}/projects", json={"name": name}).json()["id"]
    client.post(f"/api/projects/{pid}/profile-readiness/acknowledgement")
    client.post(
        f"/api/projects/{pid}/profile-readiness/transitions",
        json={"next_state": "Intake complete", "decision_note": "test"},
    )
    aid = client.post(f"/api/projects/{pid}/assessments").json()["id"]
    assert (
        client.put(
            f"/api/assessments/{aid}/determinations/{RECORD}", json={"status": "Not Met"}
        ).status_code
        == 200
    )
    rec = f"/api/projects/{pid}/assessments/{aid}/records/{RECORD}/reconciliation"
    saved = client.put(
        rec, json={"outcome": "create", "title": "Finding", "action_title": "Action"}
    ).json()
    return pid, aid, saved["corrective_action_id"]


def vpath(pid: str, aid: str, action: str) -> str:
    return (
        f"/api/projects/{pid}/assessments/{aid}/records/{RECORD}"
        f"/corrective-actions/{action}/validation"
    )


def make_ready(client: TestClient, pid: str, action: str) -> None:
    assert (
        client.put(
            f"/api/projects/{pid}/corrective-actions/{action}",
            json={"state": "Ready for Validation"},
        ).status_code
        == 200
    )


def test_ready_preserves_determination_and_finding(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as c:
        pid, aid, action = setup_case(c)
        make_ready(c, pid, action)
        direct_met = c.put(
            f"/api/assessments/{aid}/determinations/{RECORD}",
            json={"status": "Met", "interview_observation": "Attempted bypass."},
        )
        assert direct_met.status_code == 422
        state = c.get(vpath(pid, aid, action)).json()
        assert state["determination"]["status"] == "Not Met"
        assert state["finding"]["status"] == "Open"


def test_validated_interview_closes_action_leaves_finding_open(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as c:
        pid, aid, action = setup_case(c)
        assert (
            c.put(
                f"/api/assessments/{aid}/determinations/{RECORD}",
                json={"status": "Not Met", "interview_observation": "Observed safeguard."},
            ).status_code
            == 200
        )
        make_ready(c, pid, action)
        result = c.post(
            vpath(pid, aid, action), json={"outcome": "Validated", "notes": "Interview reviewed."}
        )
        assert result.status_code == 200, result.text
        state = c.get(vpath(pid, aid, action)).json()
        assert state["determination"]["status"] == "Met"
        assert state["finding"]["status"] == "Open"
        assert state["corrective_action"]["status"] == "Closed"
        assert state["corrective_action"]["validation_state"] == "Validated"
        assert len(state["events"]) == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "select prior_status,new_status from determination_history"
        ).fetchone() == ("Not Met", "Met")


def test_failed_requires_notes_and_returns_in_progress(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as c:
        pid, aid, action = setup_case(c)
        make_ready(c, pid, action)
        path = vpath(pid, aid, action)
        assert c.post(path, json={"outcome": "Failed", "notes": " "}).status_code == 422
        assert (
            c.post(path, json={"outcome": "Failed", "notes": "Insufficient evidence."}).status_code
            == 200
        )
        state = c.get(path).json()
        assert state["determination"]["status"] == "Not Met"
        assert state["corrective_action"]["status"] == "In Progress"
        assert state["events"][0]["outcome"] == "Failed"


def test_missing_integrity_evidence_is_atomic(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as c:
        pid, aid, action = setup_case(c)
        make_ready(c, pid, action)
        path = vpath(pid, aid, action)
        before = c.get(path).json()
        assert c.post(path, json={"outcome": "Validated", "notes": "No proof."}).status_code == 422
        after = c.get(path).json()
        assert after["determination"] == before["determination"]
        assert after["corrective_action"] == before["corrective_action"]
        assert after["events"] == []


def test_actor_and_cross_project_guesses_denied(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as c:
        pid, aid, action = setup_case(c, "one")
        other_pid, other_aid, other_action = setup_case(c, "two")
        make_ready(c, pid, action)
        assert (
            c.post(
                vpath(pid, aid, action),
                json={"outcome": "Failed", "notes": "x", "actor_id": "ghost"},
            ).status_code
            == 422
        )
        assert (
            c.post(
                vpath(pid, aid, other_action), json={"outcome": "Failed", "notes": "x"}
            ).status_code
            == 404
        )
        assert (
            c.post(
                vpath(other_pid, other_aid, action), json={"outcome": "Failed", "notes": "x"}
            ).status_code
            == 404
        )


def test_terminal_transition_and_event_immutable(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as c:
        pid, aid, action = setup_case(c)
        make_ready(c, pid, action)
        path = vpath(pid, aid, action)
        event = c.post(path, json={"outcome": "Failed", "notes": "No proof."}).json()
        assert (
            c.put(
                f"/api/projects/{pid}/corrective-actions/{action}", json={"state": "Closed"}
            ).status_code
            == 422
        )
    with sqlite3.connect(db) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("update validation_events set notes='tampered' where id=?", (event["id"],))
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("delete from validation_events where id=?", (event["id"],))


def test_validated_history_persists_across_restart(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    storage = tmp_path / "files"
    with TestClient(create_app(database_path=db, storage_path=storage)) as c:
        pid, aid, action = setup_case(c)
        c.put(
            f"/api/assessments/{aid}/determinations/{RECORD}",
            json={"status": "Not Met", "interview_observation": "Observed control."},
        )
        make_ready(c, pid, action)
        response = c.post(
            vpath(pid, aid, action),
            json={"outcome": "Validated", "notes": "Control retested."},
        )
        assert response.status_code == 200

    with TestClient(create_app(database_path=db, storage_path=storage)) as restarted:
        state = restarted.get(vpath(pid, aid, action)).json()
        assert state["determination"]["status"] == "Met"
        assert state["corrective_action"]["status"] == "Closed"
        assert state["events"][0]["prior_determination"] == "Not Met"
        assert state["events"][0]["evidence_context"] == {
            "presented": [],
            "interview_observation": "Observed control.",
        }
