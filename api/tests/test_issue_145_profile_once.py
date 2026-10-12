"""The Profile is approved once per version; approving is the Profile-complete act (#145)."""

import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_issue_62_versioned_profile import (
    create_project,
    lifecycle_payload,
    profile_payload,
    resolved_profile_payload,
)


def _client(tmp_path: Path) -> tuple[TestClient, Path]:
    db = tmp_path / "db.sqlite"
    return TestClient(create_app(database_path=db, storage_path=tmp_path / "files")), db


def _draft(client: TestClient, project: str, with_unknown: bool = False) -> dict[str, Any]:
    version = client.get(f"/api/projects/{project}/profile").json()["versions"][0]
    make = profile_payload if with_unknown else resolved_profile_payload
    saved = client.put(
        f"/api/projects/{project}/profile/versions/{version['id']}",
        json=make(version["content_revision"]),
    )
    assert saved.status_code == 200, saved.text
    return dict(saved.json())


def _approve(client: TestClient, project: str, version: str, **changes: str) -> Response:
    return client.post(
        f"/api/projects/{project}/profile/versions/{version}/lifecycle",
        json={**lifecycle_payload(client, project, version, "Approved"), **changes},
    )


def _history(client: TestClient, project: str) -> list[tuple[str, str]]:
    rows = client.get(f"/api/projects/{project}/profile-readiness/transitions").json()
    return [(row["prior_state"], row["next_state"]) for row in rows]


def _state(client: TestClient, project: str) -> str:
    return str(client.get(f"/api/projects/{project}/profile-readiness").json()["state"])


def test_draft_to_approved_in_one_call_records_profile_complete(tmp_path: Path) -> None:
    client, db = _client(tmp_path)
    with client:
        project = create_project(client, "once")
        version = _draft(client, project)
        assert _state(client, project) == "Intake started"
        # No reviewer is typed: the account is the reviewer.
        response = client.post(
            f"/api/projects/{project}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Approved",
                "expected_revision": version["content_revision"],
            },
        )
        assert response.status_code == 201, response.text
        approved = response.json()["version"]
        assert [e["status"] for e in approved["lifecycle"]] == ["Draft", "Approved"]
        assert approved["lifecycle"][-1]["reviewer"] == "Johnathan"
        assert response.json()["active_version_id"] == version["id"]

        # Walked from Intake started: Intake complete first, then Profile complete.
        assert _history(client, project)[-2:] == [
            ("Intake started", "Intake complete"),
            ("Intake complete", "Profile complete"),
        ]
        assert _state(client, project) == "Profile complete"
        latest = client.get(f"/api/projects/{project}/profile-readiness/transitions").json()[-1]
        assert latest["reviewed_by"] == "Johnathan"
        assert latest["approval_evidence"]
        assert "Profile version 1 approved by Johnathan" in latest["decision_note"]
    with sqlite3.connect(db) as connection:
        actions = [
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_events WHERE action LIKE 'profile.%' ORDER BY rowid"
            )
        ]
    assert "profile.version_approved" in actions
    assert actions.count("profile.readiness_transitioned") == 2


def test_a_project_already_at_intake_complete_only_gains_profile_complete(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "intake-done")
        assert client.post(f"/api/projects/{project}/start-assessment").status_code == 201
        before = _history(client, project)
        assert _state(client, project) == "Intake complete"
        version = _draft(client, project)
        assert _approve(client, project, version["id"]).status_code == 201
        assert _history(client, project) == [*before, ("Intake complete", "Profile complete")]


def test_a_second_version_does_not_repeat_profile_complete(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "second-version")
        first = _draft(client, project)
        assert _approve(client, project, first["id"]).status_code == 201
        rows = len(_history(client, project))
        created = client.post(
            f"/api/projects/{project}/profile/versions", json={"base_version_id": first["id"]}
        )
        assert created.status_code == 201, created.text
        assert _approve(client, project, created.json()["id"]).status_code == 201
        assert len(_history(client, project)) == rows
        assert _state(client, project) == "Profile complete"


def test_a_manual_profile_complete_is_refused(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "manual")
        assert (
            client.post(
                f"/api/projects/{project}/profile-readiness/transitions",
                json={"next_state": "Intake complete", "decision_note": "Intake is done."},
            ).status_code
            == 201
        )
        manual = client.post(
            f"/api/projects/{project}/profile-readiness/transitions",
            json={
                "next_state": "Profile complete",
                "decision_note": "Trying to skip the approval.",
                "reviewed_by": "Someone",
                "approval_evidence": "Said so.",
            },
        )
        assert manual.status_code == 422
        assert manual.json()["detail"] == "Approve the Profile version instead."
        assert _state(client, project) == "Intake complete"


def test_unresolved_required_fields_still_block_approval(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "unresolved")
        version = _draft(client, project)
        followed_up = client.post(
            f"/api/projects/{project}/profile-readiness/transitions",
            json={
                "next_state": "Needs follow-up",
                "decision_note": "A required detail is unknown.",
                "unresolved_required_fields": ["Number of endpoints"],
                "follow_up_work": "Ask the client for an endpoint count.",
            },
        )
        assert followed_up.status_code == 201, followed_up.text
        blocked = _approve(client, project, version["id"])
        assert blocked.status_code == 422
        assert "unresolved required fields" in blocked.json()["detail"]
        # Nothing was recorded: still a Draft, still needs follow-up, nothing active.
        detail = client.get(f"/api/projects/{project}/profile/versions/{version['id']}").json()
        assert [e["status"] for e in detail["lifecycle"]] == ["Draft"]
        assert _state(client, project) == "Needs follow-up"
        assert client.get(f"/api/projects/{project}/profile").json()["active_version_id"] is None

        resolved = client.post(
            f"/api/projects/{project}/profile-readiness/transitions",
            json={"next_state": "Intake complete", "decision_note": "The count is now known."},
        )
        assert resolved.status_code == 201, resolved.text
        assert _approve(client, project, version["id"]).status_code == 201
        assert _state(client, project) == "Profile complete"


def test_a_version_the_old_chain_left_reviewed_can_still_be_approved(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "legacy-reviewed")
        version = _draft(client, project)
        reviewed = client.post(
            f"/api/projects/{project}/profile/versions/{version['id']}/lifecycle",
            json=lifecycle_payload(client, project, version["id"], "Reviewed"),
        )
        assert reviewed.status_code == 201, reviewed.text
        assert _state(client, project) == "Intake started"  # review alone is not completion
        assert _approve(client, project, version["id"]).status_code == 201
        assert _state(client, project) == "Profile complete"


def test_approval_cannot_be_repeated_or_use_a_stale_revision(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "repeat")
        version = _draft(client, project)
        stale = _approve(client, project, version["id"], expected_revision="not-current")
        assert stale.status_code == 409
        assert _approve(client, project, version["id"]).status_code == 201
        again = _approve(client, project, version["id"])
        assert again.status_code == 422
        unknown = _approve(client, project, version["id"], actor_id="nobody")
        assert unknown.status_code == 422


def _codes(client: TestClient, project: str) -> set[str]:
    assessment = client.get(f"/api/projects/{project}/assessment").json()["id"]
    ready = client.get(f"/api/projects/{project}/assessments/{assessment}/close-readiness").json()
    return {item["code"] for item in ready["blockers"]}


def test_a_version_with_unknowns_is_approved_but_profile_complete_is_not_recorded(
    tmp_path: Path,
) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "unknowns")
        version = _draft(client, project, with_unknown=True)
        response = _approve(client, project, version["id"])
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["version"]["status"] == "Approved"
        assert body["profile_complete"] is False
        assert body["message"] == (
            "Approved. Profile complete is recorded once the follow-up items are resolved."
        )
        assert _state(client, project) == "Intake started"
        assert client.post(f"/api/projects/{project}/start-assessment").status_code == 201
        codes = _codes(client, project)
        assert {"profile_not_complete", "profile_unknown"} <= codes


def test_approval_never_overrides_needs_follow_up_until_the_unknowns_are_resolved(
    tmp_path: Path,
) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "follow-up-kept")
        version = _draft(client, project, with_unknown=True)
        assert client.post(f"/api/projects/{project}/start-assessment").status_code == 201
        recorded = client.post(
            f"/api/projects/{project}/profile-readiness/transitions",
            json={
                "next_state": "Needs follow-up",
                "decision_note": "Endpoint count unknown.",
                "follow_up_work": "Count the endpoints.",
            },
        )
        assert recorded.status_code == 201, recorded.text
        assert _approve(client, project, version["id"]).json()["profile_complete"] is False
        assert _state(client, project) == "Needs follow-up"

        # Resolution path: a new version without the unknown, approved, completes the Profile.
        created = client.post(
            f"/api/projects/{project}/profile/versions", json={"base_version_id": version["id"]}
        ).json()
        saved = client.put(
            f"/api/projects/{project}/profile/versions/{created['id']}",
            json=resolved_profile_payload(created["content_revision"]),
        )
        assert saved.status_code == 200, saved.text
        done = _approve(client, project, created["id"])
        assert done.status_code == 201, done.text
        assert done.json()["profile_complete"] is True
        assert _state(client, project) == "Profile complete"
        assert "profile_not_complete" not in _codes(client, project)
        assert "profile_unknown" not in _codes(client, project)


def test_a_copied_version_with_inventory_can_be_edited_and_saved(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with client:
        project = create_project(client, "resave")
        first = _draft(client, project, with_unknown=True)
        assert _approve(client, project, first["id"]).status_code == 201
        created = client.post(
            f"/api/projects/{project}/profile/versions", json={"base_version_id": first["id"]}
        ).json()
        saved = client.put(
            f"/api/projects/{project}/profile/versions/{created['id']}",
            json=resolved_profile_payload(created["content_revision"]),
        )
        assert saved.status_code == 200, saved.text
        kinds = {item["item_type"] for item in saved.json()["items"]}
        assert "scope_item" in kinds and "unknown_follow_up" not in kinds
