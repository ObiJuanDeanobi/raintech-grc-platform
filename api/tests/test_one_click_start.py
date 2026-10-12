"""One-click start: creating the first assessment records intake in the same step."""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_61_profile_readiness import create_project, readiness_path, transition


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _rows(tmp_path: Path, sql: str, *args: str) -> list[tuple[object, ...]]:
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        return connection.execute(sql, args).fetchall()


def test_start_from_intake_started_creates_assessment_and_records_intake(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = create_project(client, "start")
        response = client.post(f"/api/projects/{project}/start-assessment")
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["assessment"]["project_id"] == project
        assert body["readiness"]["state"] == "Intake complete"
        assert body["readiness"]["assessment_exists"] is True

        history = client.get(f"{readiness_path(project)}/transitions").json()
        assert [(h["prior_state"], h["next_state"]) for h in history] == [
            ("Intake started", "Intake started"),
            ("Intake started", "Intake complete"),
        ]
        assert history[-1]["decision_note"].startswith("Intake recorded when the assessment")
    actions = [
        row[0]
        for row in _rows(
            tmp_path,
            "SELECT action FROM audit_events WHERE entity_id IN (?, ?) ORDER BY rowid",
            project,
            body["assessment"]["id"],
        )
    ]
    assert "profile.readiness_transitioned" in actions
    assert "assessment.created" in actions
    assert actions.index("profile.readiness_transitioned") < actions.index("assessment.created")


def test_profile_complete_is_still_a_separate_step(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = create_project(client, "later")
        client.post(f"/api/projects/{project}/start-assessment")
        readiness = client.get(readiness_path(project)).json()
        assert readiness["state"] == "Intake complete"
        assert readiness["profile_completion_blocking_reasons"]


def test_needs_follow_up_is_refused_and_nothing_is_created(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = create_project(client, "follow-up")
        assert (
            transition(
                client, project, "Needs follow-up", "Waiting on the client", follow_up_work="Ask"
            ).status_code
            == 201
        )
        before = _rows(tmp_path, "SELECT COUNT(*) FROM profile_readiness_transitions")
        response = client.post(f"/api/projects/{project}/start-assessment")
        assert response.status_code == 409
        assert "follow-up" in str(response.json()["detail"])
        assert _rows(tmp_path, "SELECT COUNT(*) FROM assessments") == [(0,)]
        assert _rows(tmp_path, "SELECT COUNT(*) FROM profile_readiness_transitions") == before


def test_existing_assessment_is_refused(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = create_project(client, "twice")
        assert client.post(f"/api/projects/{project}/start-assessment").status_code == 201
        assert client.post(f"/api/projects/{project}/start-assessment").status_code == 409
        assert _rows(tmp_path, "SELECT COUNT(*) FROM assessments") == [(1,)]
        assert _rows(tmp_path, "SELECT COUNT(*) FROM profile_readiness_transitions") == [(2,)]


def test_unknown_project_is_404(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.post("/api/projects/missing/start-assessment").status_code == 404


def test_old_assessment_endpoint_still_requires_intake(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = create_project(client, "old")
        blocked = client.post(f"/api/projects/{project}/assessments")
        assert blocked.status_code == 409
        assert transition(client, project, "Intake complete", "Intake done").status_code == 201
        created = client.post(f"/api/projects/{project}/assessments")
        assert created.status_code == 201
        assert client.post(f"/api/projects/{project}/assessments").status_code == 409
