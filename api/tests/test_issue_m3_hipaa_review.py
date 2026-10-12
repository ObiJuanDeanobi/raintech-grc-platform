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


def _sign_off(client: TestClient, project: str, package_id: str, **changes: Any) -> httpx.Response:
    """The one sign-off: the reviewer is the account, the note is optional (issue #145)."""
    payload = {"actor_id": "johnathan", "note": "Reviewed the exact package."}
    payload.update(changes)
    return client.post(
        f"/api/projects/{project}/packages/{package_id}/review/sign-off", json=payload
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
        response = _sign_off(client, project, package["id"])
        assert response.status_code == 201, response.text
        assert response.json()["state"] == "Ready to issue"
        ready = response.json()
        # One act, one event: no In Review or Reviewed step on the way.
        assert len(ready["events"]) == 1
        event = ready["events"][-1]
        assert event["prior_state"] == "Complete candidate"
        assert event["reviewer_name"] == "Johnathan"
        assert event["reviewer_role"] == ""
        assert event["package_sha256"]
        assert event["source_snapshot_sha256"]
        assert event["component_hashes_json"]
        assert event["template_hashes_json"]
        assert "fieldwork_ready_for_generation" in event["close_decision_json"]
    with sqlite3.connect(db) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE action='hipaa_package_review_transition'"
            ).fetchone()[0]
            == 1
        )


def test_review_rejects_second_sign_off_and_database_rejects_unsigned_events(
    tmp_path: Path,
) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-invalid")
        package = _package(client, project, assessment)
        assert _sign_off(client, project, package["id"]).status_code == 201
        again = _sign_off(client, project, package["id"])
        assert again.status_code == 409
        assert "already been signed off" in again.json()["detail"]
        # The reviewer is the account, so a person who is not an account cannot sign.
        other = _package(client, project, assessment)
        assert _sign_off(client, project, other["id"], actor_id="nobody").status_code == 422
    with sqlite3.connect(db) as connection:
        base = connection.execute("SELECT * FROM package_review_events").fetchone()
        assert base is not None
    with sqlite3.connect(db) as connection:
        other_id = connection.execute(
            "SELECT id FROM generated_packages WHERE id != ? ORDER BY created_at DESC LIMIT 1",
            (package["id"],),
        ).fetchone()[0]
        for blank in ("reviewer_name", "approval"):
            with pytest.raises(sqlite3.IntegrityError, match="invalid package review transition"):
                connection.execute(
                    f"""INSERT INTO package_review_events
                           SELECT 'blank-{blank}', project_id, assessment_id, ?, 1,
                                  'Complete candidate', 'Ready to issue', actor_id,
                                  {'""' if blank == "reviewer_name" else "reviewer_name"},
                                  reviewer_role, note,
                                  {'""' if blank == "approval" else "approval"},
                                  confirmations_json, package_sha256,
                                  source_snapshot_id, source_snapshot_sha256, template_version,
                                  component_ids_json, component_hashes_json, template_hashes_json,
                                  close_decision_json, created_at
                       FROM package_review_events LIMIT 1""",
                    (other_id,),
                )


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
        blocked = _sign_off(client, project, package["id"])
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
        assert _sign_off(client, other, package["id"]).status_code == 404
        assert _sign_off(client, project, package["id"]).status_code == 201
    restarted, _ = _app(tmp_path)
    with restarted:
        review = restarted.get(f"/api/projects/{project}/packages/{package['id']}/review")
        assert review.status_code == 200
        assert review.json()["state"] == "Ready to issue"


def test_database_rejects_event_mutation_deletion_and_reordering(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "review-sql")
        package = _package(client, project, assessment)
        assert _sign_off(client, project, package["id"]).status_code == 201
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
                              'Complete candidate', 'Ready to issue', actor_id,
                              reviewer_name, reviewer_role, note, approval, confirmations_json,
                              package_sha256,
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
                                  'Complete candidate', 'Ready to issue', actor_id,
                                  reviewer_name, reviewer_role, note, approval, confirmations_json,
                                  package_sha256,
                                  source_snapshot_id, source_snapshot_sha256, template_version,
                                  component_ids_json, component_hashes_json, {template_expression},
                                  {close_expression}, created_at
                       FROM package_review_events WHERE id=?""",
                    (event_id, row[0]),
                )
