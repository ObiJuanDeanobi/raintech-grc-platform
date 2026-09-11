"""Contract tests for exact HIPAA package review and sign-off."""

import sqlite3
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient

from api.tests.test_issue_m3_hipaa_generation import _app, _ready


def _package(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def _transition(
    client: TestClient, project: str, package_id: str, state: str, **changes: Any
) -> httpx.Response:
    payload = {
        "actor_id": "johnathan",
        "next_state": state,
        "reviewer_name": "Johnathan Dean",
        "reviewer_role": "Security Assessor",
        "note": f"Reviewed exact package for {state}.",
        "approval": "I approve this exact package for issuance."
        if state == "Ready to issue"
        else "",
        "component_confirmations": {
            "assessment_report": True,
            "poam": True,
            "__source": True,
        },
    }
    payload.update(changes)
    return client.post(
        f"/api/projects/{project}/packages/{package_id}/review/transitions", json=payload
    )


def test_review_binds_exact_package_and_reaches_ready_to_issue(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-success")
        package = _package(client, project, assessment)
        initial = client.get(f"/api/projects/{project}/packages/{package['id']}/review")
        assert initial.status_code == 200
        assert initial.json()["state"] == "Complete candidate"
        assert initial.json()["drift"] == []
        assert initial.json()["blockers"] == []
        for state in ("In Review", "Reviewed", "Ready to issue"):
            response = _transition(client, project, package["id"], state)
            assert response.status_code == 201, response.text
            assert response.json()["state"] == state
        ready = response.json()
        assert len(ready["events"]) == 3
        assert ready["events"][-1]["package_sha256"]
        assert ready["events"][-1]["source_snapshot_sha256"]
        assert ready["events"][-1]["component_hashes_json"]
        assert ready["events"][-1]["template_hashes_json"]
        assert "fieldwork_ready_for_generation" in ready["events"][-1]["close_decision_json"]
    with sqlite3.connect(db) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE action='hipaa_package_review_transition'"
            ).fetchone()[0]
            == 3
        )


def test_review_rejects_skips_missing_confirmation_and_missing_approval(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-invalid")
        package = _package(client, project, assessment)
        skipped = _transition(client, project, package["id"], "Reviewed")
        assert skipped.status_code == 409
        assert "Invalid transition" in skipped.json()["detail"]
        assert _transition(client, project, package["id"], "In Review").status_code == 201
        missing = _transition(
            client,
            project,
            package["id"],
            "Reviewed",
            component_confirmations={"assessment_report": True, "__source": True},
        )
        assert missing.status_code == 409
        assert "confirmed" in missing.json()["detail"]
        assert _transition(client, project, package["id"], "Reviewed").status_code == 201
        unsigned = _transition(client, project, package["id"], "Ready to issue", approval="")
        assert unsigned.status_code == 409
        assert "approval" in unsigned.json()["detail"]


def test_source_drift_blocks_review_without_mutating_package(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-drift")
        package = _package(client, project, assessment)
        with sqlite3.connect(db) as connection:
            connection.execute(
                "UPDATE determinations SET interview_observation=? WHERE assessment_id=?",
                ("Changed after package generation.", assessment),
            )
            connection.commit()
        review = client.get(f"/api/projects/{project}/packages/{package['id']}/review")
        assert review.status_code == 200
        assert "Assessment source changed after generation" in review.json()["drift"]
        blocked = _transition(client, project, package["id"], "In Review")
        assert blocked.status_code == 409
        assert "source changed" in blocked.json()["detail"]
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM package_review_events").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT state FROM generated_packages WHERE id=?", (package["id"],)
            ).fetchone()[0]
            == "promoted"
        )


def test_review_is_project_isolated_and_survives_restart(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-one")
        other, _ = _ready(client, db, "review-two")
        package = _package(client, project, assessment)
        assert (
            client.get(f"/api/projects/{other}/packages/{package['id']}/review").status_code == 404
        )
        assert _transition(client, other, package["id"], "In Review").status_code == 404
        assert _transition(client, project, package["id"], "In Review").status_code == 201
    restarted, _ = _app(tmp_path)
    with restarted:
        review = restarted.get(f"/api/projects/{project}/packages/{package['id']}/review")
        assert review.status_code == 200
        assert review.json()["state"] == "In Review"


def test_database_rejects_event_mutation_deletion_and_reordering(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-sql")
        package = _package(client, project, assessment)
        assert _transition(client, project, package["id"], "In Review").status_code == 201
    with sqlite3.connect(db) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE package_review_events SET note='forged'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM package_review_events")
        row = connection.execute("SELECT * FROM package_review_events").fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="invalid package review transition"):
            connection.execute(
                """INSERT INTO package_review_events
                       SELECT 'forged', project_id, assessment_id, package_id, 3,
                              'In Review', 'Ready to issue', actor_id, reviewer_name, reviewer_role,
                              note, approval, confirmations_json, package_sha256,
                              source_snapshot_id, source_snapshot_sha256, template_version,
                              component_ids_json, component_hashes_json, template_hashes_json,
                              close_decision_json, created_at
                   FROM package_review_events WHERE id=?""",
                (row[0],),
            )
        for event_id, template_expression, close_expression in (
            (
                "missing-template-key",
                "json_remove(template_hashes_json, '$.poam')",
                "close_decision_json",
            ),
            (
                "forged-close-decision",
                "template_hashes_json",
                "json_set(close_decision_json, '$.decision', 'forged')",
            ),
        ):
            with pytest.raises(sqlite3.IntegrityError, match="invalid package review transition"):
                connection.execute(
                    f"""INSERT INTO package_review_events
                           SELECT ?, project_id, assessment_id, package_id, 2,
                                  'In Review', 'Reviewed', actor_id, reviewer_name, reviewer_role,
                                  note, approval, confirmations_json, package_sha256,
                                  source_snapshot_id, source_snapshot_sha256, template_version,
                                  component_ids_json, component_hashes_json, {template_expression},
                                  {close_expression}, created_at
                       FROM package_review_events WHERE id=?""",
                    (event_id, row[0]),
                )
