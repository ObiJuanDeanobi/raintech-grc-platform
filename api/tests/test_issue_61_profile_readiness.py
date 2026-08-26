import json
import sqlite3
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_workspace_api import migration_config

BOUNDARY_DOCUMENT = "docs/local-evidence-operating-boundary.md"


def create_project(client: TestClient, suffix: str) -> str:
    client_id = client.post("/api/clients", json={"name": f"Synthetic Client {suffix}"}).json()[
        "id"
    ]
    response = client.post(
        f"/api/clients/{client_id}/projects",
        json={"name": f"HIPAA Readiness {suffix}"},
    )
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def readiness_path(project_id: str) -> str:
    return f"/api/projects/{project_id}/profile-readiness"


def transition(
    client: TestClient,
    project_id: str,
    next_state: str,
    note: str,
    *,
    unresolved_required_fields: list[str] | None = None,
    follow_up_work: str = "",
    reviewed_by: str = "",
    approval_evidence: str = "",
) -> Response:
    return client.post(
        f"{readiness_path(project_id)}/transitions",
        json={
            "next_state": next_state,
            "decision_note": note,
            "unresolved_required_fields": unresolved_required_fields or [],
            "follow_up_work": follow_up_work,
            "reviewed_by": reviewed_by,
            "approval_evidence": approval_evidence,
        },
    )


def acknowledge_boundary(client: TestClient, project_id: str) -> Response:
    return client.post(f"{readiness_path(project_id)}/acknowledgement")


def test_readiness_path_gates_new_assessments_and_keeps_existing_assessment_readable(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "A")
        initial = client.get(readiness_path(project_id))
        assert initial.status_code == 200
        assert initial.json()["state"] == "Intake started"
        assert initial.json()["assessment_exists"] is False
        assert initial.json()["supported_states"] == [
            "Intake started",
            "Intake complete",
            "Needs follow-up",
            "Profile complete",
        ]
        assert initial.json()["allowed_next_states"] == [
            "Intake complete",
            "Needs follow-up",
        ]
        assert initial.json()["assessment_entry_allowed"] is False
        assert initial.json()["assessment_entry_blocking_reasons"]
        blocked = client.post(f"/api/projects/{project_id}/assessments")
        assert blocked.status_code == 409
        assert blocked.json()["detail"] == initial.json()["assessment_entry_blocking_reasons"]

        acknowledgement = acknowledge_boundary(client, project_id)
        assert acknowledgement.status_code == 201
        assert acknowledgement.json()["document_path"] == BOUNDARY_DOCUMENT
        assert acknowledgement.json()["statement"] == (
            "Acknowledges review of the local evidence operating boundary; "
            "this is not an attestation that content is free of CUI, PHI, or ePHI."
        )

        intake_complete = transition(
            client,
            project_id,
            "Intake complete",
            "Initial intake reviewed; one required fact remains explicit.",
            unresolved_required_fields=["Security officer"],
            follow_up_work="Confirm the named security officer in the next client interview.",
        )
        assert intake_complete.status_code == 201
        assert intake_complete.json()["state"] == "Intake complete"
        assert intake_complete.json()["assessment_entry_allowed"] is True
        assert intake_complete.json()["profile_completion_blocking_reasons"] == [
            "Resolve required field: Security officer.",
            "Record a named reviewer.",
            "Record review or approval evidence.",
        ]

        created = client.post(f"/api/projects/{project_id}/assessments")
        assert created.status_code == 201
        assessment_id = created.json()["id"]
        assert client.get(readiness_path(project_id)).json()["assessment_exists"] is True
        assert client.get(f"/api/projects/{project_id}/assessment").status_code == 200

        follow_up = transition(
            client,
            project_id,
            "Needs follow-up",
            "New scope question requires follow-up.",
            unresolved_required_fields=["Security officer"],
            follow_up_work="Confirm the named security officer.",
        )
        assert follow_up.status_code == 201
        assert follow_up.json()["assessment_entry_allowed"] is False
        assert follow_up.json()["current_details"]["follow_up_work"] == (
            "Confirm the named security officer."
        )
        assert follow_up.json()["assessment_entry_blocking_reasons"] == [
            "Resolve the recorded follow-up before starting a new assessment."
        ]
        assert client.post(f"/api/projects/{project_id}/assessments").status_code == 409
        assert (
            client.get(
                f"/api/projects/{project_id}/assessments/{assessment_id}"
                "/records/164.308(a)(1)(ii)(A)"
            ).status_code
            == 200
        )

        complete = transition(
            client,
            project_id,
            "Profile complete",
            "All required facts resolved and approved.",
            reviewed_by="Johnathan",
            approval_evidence="Review meeting recorded in synthetic engagement notes.",
        )
        assert complete.status_code == 201
        assert complete.json()["state"] == "Profile complete"
        assert complete.json()["assessment_entry_allowed"] is True
        assert complete.json()["profile_completion_blocking_reasons"] == []

        history = client.get(f"{readiness_path(project_id)}/transitions").json()
        assert [(item["prior_state"], item["next_state"]) for item in history][-3:] == [
            ("Intake started", "Intake complete"),
            ("Intake complete", "Needs follow-up"),
            ("Needs follow-up", "Profile complete"),
        ]
        assert all(item["actor"]["id"] == "johnathan" for item in history)
        assert all(item["timestamp"] and item["decision_note"] for item in history)


def test_unknown_follow_up_approval_and_acknowledgement_rules_are_enforced(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Rules")
        missing_ack = transition(
            client,
            project_id,
            "Intake complete",
            "Try without acknowledgement.",
        )
        assert missing_ack.status_code == 422
        assert "operating boundary" in missing_ack.json()["detail"]
        acknowledge_boundary(client, project_id)

        follow_up_without_work = transition(
            client,
            project_id,
            "Needs follow-up",
            "Follow-up is needed.",
        )
        assert follow_up_without_work.status_code == 422
        assert follow_up_without_work.json()["detail"] == (
            "Needs follow-up requires explicit follow-up work"
        )

        unknown_without_work = transition(
            client,
            project_id,
            "Intake complete",
            "Unknown is declared.",
            unresolved_required_fields=["System inventory"],
        )
        assert unknown_without_work.status_code == 422
        assert "follow-up work" in unknown_without_work.json()["detail"]

        assert (
            transition(
                client,
                project_id,
                "Intake complete",
                "Unknown has explicit follow-up.",
                unresolved_required_fields=["System inventory"],
                follow_up_work="Validate inventory with the system owner.",
            ).status_code
            == 201
        )
        unresolved_complete = transition(
            client,
            project_id,
            "Profile complete",
            "Attempt completion before resolution.",
            unresolved_required_fields=["System inventory"],
            reviewed_by="Johnathan",
            approval_evidence="Synthetic review record.",
        )
        assert unresolved_complete.status_code == 422
        assert "unresolved required fields" in unresolved_complete.json()["detail"]

        unnamed_review = transition(
            client,
            project_id,
            "Profile complete",
            "Attempt completion without named review.",
        )
        assert unnamed_review.status_code == 422
        assert "named reviewer" in unnamed_review.json()["detail"]

        no_evidence = transition(
            client,
            project_id,
            "Profile complete",
            "Attempt completion without approval evidence.",
            reviewed_by="Johnathan",
        )
        assert no_evidence.status_code == 422
        assert "approval evidence" in no_evidence.json()["detail"]


def test_two_project_isolation_restart_persistence_and_append_only_history(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        project_a = create_project(client, "A")
        project_b = create_project(client, "B")
        acknowledge_boundary(client, project_a)
        assert (
            transition(
                client,
                project_a,
                "Intake complete",
                "Project A is ready.",
            ).status_code
            == 201
        )
        assessment_id = client.post(f"/api/projects/{project_a}/assessments").json()["id"]

        assert client.get(readiness_path(project_b)).json()["state"] == "Intake started"
        assert client.get(f"{readiness_path(project_b)}/transitions").json()[0][
            "next_state"
        ] == "Intake started"
        assert client.post(f"/api/projects/{project_b}/assessments").status_code == 409
        assert (
            client.get(
                f"/api/projects/{project_b}/assessments/{assessment_id}"
                "/records/164.308(a)(1)(ii)(A)"
            ).status_code
            == 404
        )
        assert client.get("/api/projects/missing/profile-readiness").status_code == 404

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        ready = client.get(readiness_path(project_a)).json()
        assert ready["state"] == "Intake complete"
        assert ready["acknowledgement"]["actor"]["id"] == "johnathan"
        assert client.get(f"{readiness_path(project_a)}/transitions").json()[-1][
            "decision_note"
        ] == "Project A is ready."
        assert client.get(f"/api/projects/{project_a}/assessment").json()["id"] == assessment_id

    with sqlite3.connect(database_path) as connection:
        audit_rows = connection.execute(
            "SELECT action, actor_id FROM audit_events WHERE entity_id = ? ORDER BY created_at",
            (project_a,),
        ).fetchall()
        assert ("profile.boundary_acknowledged", "johnathan") in audit_rows
        assert ("profile.readiness_transitioned", "johnathan") in audit_rows
        transition_id = connection.execute(
            "SELECT id FROM profile_readiness_transitions WHERE project_id = ? "
            "ORDER BY created_at LIMIT 1",
            (project_a,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE profile_readiness_transitions SET decision_note = 'changed' WHERE id = ?",
                (transition_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM profile_readiness_transitions WHERE id = ?",
                (transition_id,),
            )
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "UPDATE projects SET profile_readiness_state = 'Profile complete' WHERE id = ?",
                (project_a,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="continuous"):
            connection.execute(
                """
                INSERT INTO profile_readiness_transitions(
                    id, project_id, prior_state, next_state, actor_id, decision_note,
                    unresolved_required_fields_json, follow_up_work, reviewed_by,
                    approval_evidence, created_at
                ) VALUES (
                    'discontinuous-transition', ?, 'Intake started', 'Profile complete',
                    'johnathan', 'Invalid direct SQL transition.', '[]', '', 'Reviewer',
                    'Evidence', '2026-08-26T12:00:00+00:00'
                )
                """,
                (project_a,),
            )


def test_readiness_behavior_consumes_the_persisted_framework_declaration(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Declaration")
        with sqlite3.connect(database_path) as connection:
            row = connection.execute(
                "SELECT declarations_json FROM framework_versions "
                "WHERE id = 'hipaa-45cfr164-2026-07-01'"
            ).fetchone()
            declarations = json.loads(row[0])
            declarations["profile_readiness"] = {
                "states": [
                    "Intake started",
                    "Intake complete",
                    "Needs follow-up",
                    "Profile complete",
                ],
                "transitions": {
                    "Intake started": ["Profile complete"],
                    "Intake complete": [],
                    "Needs follow-up": [],
                    "Profile complete": [],
                },
                "assessment_entry": {
                    "allowed_states": ["Intake started"],
                    "blocking_reasons": {
                        "Profile complete": "Custom declaration blocks entry."
                    },
                },
                "profile_completion": {
                    "state": "Profile complete",
                    "requires_no_unresolved_required_fields": True,
                    "required_fields": {},
                },
                "follow_up_work": {
                    "required_states": ["Needs follow-up"],
                    "required_when_unresolved_required_fields": True,
                },
                "boundary_document": BOUNDARY_DOCUMENT,
            }
            connection.execute(
                "UPDATE framework_versions SET declarations_json = ? "
                "WHERE id = 'hipaa-45cfr164-2026-07-01'",
                (json.dumps(declarations),),
            )

        initial = client.get(readiness_path(project_id)).json()
        assert initial["assessment_entry_allowed"] is True
        assert initial["allowed_next_states"] == ["Profile complete"]
        acknowledge_boundary(client, project_id)
        completed = transition(
            client,
            project_id,
            "Profile complete",
            "Custom declaration allows completion without review fields.",
        )
        assert completed.status_code == 201
        assert completed.json()["assessment_entry_allowed"] is False
        assert completed.json()["assessment_entry_blocking_reasons"] == [
            "Custom declaration blocks entry."
        ]


def test_populated_0003_migration_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    config = migration_config(database_path, tmp_path / "files")
    command.upgrade(config, "0003")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO user_accounts(id, display_name) VALUES ('johnathan', 'Johnathan');
            INSERT INTO framework_versions(
                id, name, record_count, prompt_count, declarations_json
            ) VALUES (
                'hipaa-45cfr164-2026-07-01', 'HIPAA', 0, 0, '{}'
            );
            INSERT INTO clients(id, name, created_at)
            VALUES ('client-existing', 'Synthetic Existing Client', '2026-08-26T00:00:00+00:00');
            INSERT INTO projects(id, client_id, name, framework_version_id, created_at)
            VALUES (
                'project-existing', 'client-existing', 'Synthetic Existing Project',
                'hipaa-45cfr164-2026-07-01', '2026-08-26T00:00:00+00:00'
            );
            INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES (
                'assessment-existing', 'project-existing',
                'hipaa-45cfr164-2026-07-01', '2026-08-26T00:01:00+00:00'
            );
            """
        )

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }
        assert "profile_readiness_state" not in columns
        assert connection.execute(
            "SELECT prior_state, next_state, actor_id "
            "FROM profile_readiness_transitions WHERE project_id = 'project-existing'"
        ).fetchone() == ("Intake started", "Intake started", "johnathan")
        assert connection.execute(
            "SELECT id FROM assessments WHERE id = 'assessment-existing'"
        ).fetchone() == ("assessment-existing",)

    command.downgrade(config, "0003")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT id FROM assessments WHERE id = 'assessment-existing'"
        ).fetchone() == ("assessment-existing",)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }
        assert "profile_readiness_state" not in columns

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }
        assert "profile_readiness_state" not in columns
        assert connection.execute(
            "SELECT next_state FROM profile_readiness_transitions "
            "WHERE project_id = 'project-existing'"
        ).fetchone() == ("Intake started",)
