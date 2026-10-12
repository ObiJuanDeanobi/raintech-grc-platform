"""The one review-and-issue act (GitHub issue #145, ADR 0021)."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app
from api.tests.test_issue_m3_hipaa_review import _package, _sign_off
from api.tests.test_issue_m3_substantive_reopening import _issued_with_not_met, _reopen


@pytest.fixture(autouse=True)
def _no_double_submit_window(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.issuance as issuance

    monkeypatch.setattr(issuance, "DOUBLE_SUBMIT_SECONDS", 0)


def _issue(
    client: TestClient, project: str, assessment: str, note: str = "", actor: str = "johnathan"
) -> Response:
    body: dict[str, Any] = {"actor_id": actor}
    if note:
        body["note"] = note
    return client.post(f"/api/projects/{project}/assessments/{assessment}/issue", json=body)


def _count(db: Path, table: str, where: str = "1=1") -> int:
    with sqlite3.connect(db) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0])


def _lifecycles(client: TestClient, project: str) -> dict[str, str]:
    return {p["id"]: p["lifecycle"] for p in client.get(f"/api/projects/{project}/packages").json()}


def _audit_actions(db: Path) -> list[str]:
    with sqlite3.connect(db) as connection:
        return [
            row[0] for row in connection.execute("SELECT action FROM audit_events ORDER BY rowid")
        ]


def test_one_call_issues_with_reviewer_date_and_note(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-one")
        response = _issue(client, project, assessment, "Reviewed for the October report.")
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["issuance_status"] == "Current"
        assert body["reviewer"] == "Johnathan"
        assert body["note"] == "Reviewed for the October report."
        assert body["issued_at"]

        # One review sign-off in total: the reviewer is the account, nothing else asked.
        with sqlite3.connect(db) as connection:
            connection.row_factory = sqlite3.Row
            events = connection.execute("SELECT * FROM package_review_events").fetchall()
            assert len(events) == 1
            event = events[0]
            assert event["next_state"] == "Ready to issue"
            assert event["reviewer_name"] == "Johnathan"
            assert event["reviewer_role"] == ""
            assert event["note"] == "Reviewed for the October report."
            assert event["approval"].startswith("Reviewed for issue by Johnathan on ")
            assert event["confirmations_json"] == "{}"
            assert event["created_at"][:10] == body["issued_at"][:10]
            backup = connection.execute("SELECT * FROM backup_records").fetchall()
            assert [row["status"] for row in backup] == ["complete"]
            snapshot = connection.execute("SELECT * FROM issuance_snapshots").fetchone()
            assert snapshot["review_event_id"] == event["id"]
            assert snapshot["backup_id"] == backup[0]["id"]
        assert _lifecycles(client, project) == {body["package_id"]: "Issued"}
        actions = _audit_actions(db)
        for expected in (
            "hipaa_package_generated",
            "hipaa_package_review_transition",
            "hipaa_preissuance_backup_completed",
            "hipaa_package_issued",
        ):
            assert actions.count(expected) == 1, expected


def test_the_note_is_optional(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-no-note")
        assert _issue(client, project, assessment).status_code == 201
    assert _count(db, "package_review_events", "note = ''") == 1


def test_a_second_issue_supersedes_the_first(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-supersede")
        first = _issue(client, project, assessment, "First.").json()
        assert _lifecycles(client, project) == {first["package_id"]: "Issued"}
        second = _issue(client, project, assessment, "Second, presentation only.")
        assert second.status_code == 201, second.text
        second_body = second.json()
        assert second_body["superseded_package_id"] == first["package_id"]
        assert _lifecycles(client, project) == {
            first["package_id"]: "Superseded",
            second_body["package_id"]: "Issued",
        }
    with sqlite3.connect(db) as connection:
        current = [row[0] for row in connection.execute("SELECT package_id FROM current_issuances")]
    assert current == [second_body["package_id"]]
    assert _count(db, "issuance_snapshots") == 2
    assert _count(db, "issuance_supersessions") == 1


def test_changed_data_after_issue_must_go_through_reopening(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-changed")
        first = _issue(client, project, assessment).json()
        with sqlite3.connect(db) as connection:
            connection.execute(
                "UPDATE determinations SET interview_observation=? WHERE assessment_id=?",
                ("Changed after the issue.", assessment),
            )
            connection.commit()
        packages, events = _count(db, "generated_packages"), _count(db, "package_review_events")
        refused = _issue(client, project, assessment)
        assert refused.status_code == 409
        assert "Reopen the assessment" in refused.json()["detail"]
        assert _lifecycles(client, project) == {first["package_id"]: "Issued"}
    assert _count(db, "generated_packages") == packages
    assert _count(db, "package_review_events") == events
    assert _count(db, "issuance_snapshots") == 1
    assert "package.issue_failed" in _audit_actions(db)


def test_a_failing_hard_gate_returns_groups_and_writes_nothing(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-gate")
        with sqlite3.connect(db) as connection:
            record = connection.execute(
                "SELECT record_id FROM determinations WHERE assessment_id=? LIMIT 1", (assessment,)
            ).fetchone()[0]
            connection.execute(
                "UPDATE determinations SET status='' WHERE assessment_id=? AND record_id=?",
                (assessment, record),
            )
            connection.commit()
        response = _issue(client, project, assessment)
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["message"] == "Fix these before issuing."
        groups = {g["key"]: g for g in detail["groups"]}
        assert groups["undecided"]["label"] == "Specifications not decided"
        assert groups["undecided"]["count"] >= 1
        assert groups["undecided"]["target"] == "assessments"
        assert detail["blockers"]
    for table in (
        "generated_packages",
        "source_snapshots",
        "package_review_events",
        "backup_records",
        "issuance_attempts",
        "issuance_snapshots",
    ):
        assert _count(db, table) == 0, table
    assert "package.issue_blocked" in _audit_actions(db)


def test_a_failed_backup_returns_409_and_leaves_no_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance

    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-backup")
        monkeypatch.setattr(
            issuance,
            "_validate_archive",
            lambda *a, **k: (_ for _ in ()).throw(OSError("disk is full")),
        )
        failed = _issue(client, project, assessment)
        assert failed.status_code == 409
        assert failed.json()["detail"] == "Backup failed: disk is full. Nothing was issued."
        assert _count(db, "issuance_snapshots") == 0
        assert _count(db, "issuance_attempts") == 0
        assert _count(db, "backup_records", "status='failed'") == 1
        assert "hipaa_preissuance_backup_failed" in _audit_actions(db)
        # The unissued package is only a Draft.
        assert set(_lifecycles(client, project).values()) == {"Draft"}

        monkeypatch.undo()
        retried = _issue(client, project, assessment)
        assert retried.status_code == 201, retried.text


def test_a_failed_backup_keeps_the_prior_issue_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance

    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-backup-prior")
        first = _issue(client, project, assessment).json()
        monkeypatch.setattr(
            issuance,
            "_validate_archive",
            lambda *a, **k: (_ for _ in ()).throw(OSError("disk is full")),
        )
        failed = _issue(client, project, assessment)
        assert failed.status_code == 409
        assert failed.json()["detail"] == (
            "Backup failed: disk is full. Nothing was issued; "
            "the last issued version is still current."
        )
        lifecycles = _lifecycles(client, project)
        assert lifecycles[first["package_id"]] == "Issued"
        assert list(lifecycles.values()).count("Issued") == 1
        assert "Superseded" not in lifecycles.values()
    with sqlite3.connect(db) as connection:
        current = [row[0] for row in connection.execute("SELECT package_id FROM current_issuances")]
    assert current == [first["package_id"]]
    assert _count(db, "issuance_snapshots") == 1
    assert _count(db, "issuance_supersessions") == 0
    assert _count(db, "backup_records", "status='failed'") == 1


def test_issue_now_issues_a_presentation_correction_in_one_act(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-now")
        first = _issue(client, project, assessment).json()
        response = client.post(
            f"/api/projects/{project}/packages/{first['package_id']}/issue-now",
            json={"actor_id": "johnathan", "note": "Cover page wording."},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["correction"]["prior_package_id"] == first["package_id"]
        assert body["correction"]["reason"] == "Reissued by Johnathan: Cover page wording."
        assert body["superseded_package_id"] == first["package_id"]
        assert _lifecycles(client, project)[first["package_id"]] == "Superseded"
        # Only the current issue can be corrected.
        stale = client.post(
            f"/api/projects/{project}/packages/{first['package_id']}/issue-now",
            json={"actor_id": "johnathan"},
        )
        assert stale.status_code == 409
        missing = client.post(
            f"/api/projects/{project}/packages/nope/issue-now", json={"actor_id": "johnathan"}
        )
        assert missing.status_code == 404


def test_the_act_is_scoped_and_needs_a_real_account(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-scope-a")
        other, _ = _ready(client, db, "act-scope-b")
        assert _issue(client, other, assessment).status_code == 404
        assert _issue(client, project, "no-such-assessment").status_code == 404
        assert _issue(client, project, assessment, actor="nobody").status_code == 422
    assert _count(db, "issuance_snapshots") == 0


def test_a_reopened_assessment_is_issued_by_the_same_act(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior, _ = _issued_with_not_met(client, db, "act-reopen")
        with sqlite3.connect(db) as connection:
            affected = connection.execute(
                "SELECT record_id FROM determinations WHERE status='Met' LIMIT 1"
            ).fetchone()[0]
        reopened = _reopen(client, project, prior, affected=[affected]).json()
        successor = reopened["successor_assessment_id"]
        client.post(
            f"/api/projects/{project}/assessments/{successor}/records/{affected}/revalidate",
            json={"actor_id": "johnathan", "note": "Re-examined."},
        )
        issued = _issue(client, project, successor, "Reissued after reopening.")
        assert issued.status_code == 201, issued.text
        lifecycles = _lifecycles(client, project)
        assert lifecycles[prior] == "Superseded"
        assert lifecycles[issued.json()["package_id"]] == "Issued"


def test_legacy_signed_off_packages_read_as_draft_until_issued(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-legacy")
        package = _package(client, project, assessment)
        assert _sign_off(client, project, package["id"]).status_code == 201
        assert _lifecycles(client, project) == {package["id"]: "Draft"}
        issued = _issue(client, project, assessment)
        assert issued.status_code == 201, issued.text
        assert _lifecycles(client, project)[package["id"]] == "Draft"
        assert _lifecycles(client, project)[issued.json()["package_id"]] == "Issued"


def test_issue_checklist_lists_hard_gates_and_warnings(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-checklist")
        ready = client.get(f"/api/projects/{project}/assessments/{assessment}/issue-checklist")
        assert ready.status_code == 200
        body = ready.json()
        assert body["ready"] is True and body["groups"] == []
        assert body["current_issue"] is None
        with sqlite3.connect(db) as connection:
            record = connection.execute(
                "SELECT record_id FROM determinations WHERE assessment_id=? LIMIT 1", (assessment,)
            ).fetchone()[0]
            connection.execute(
                "UPDATE determinations SET status='' WHERE assessment_id=? AND record_id=?",
                (assessment, record),
            )
            connection.commit()
        blocked = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        ).json()
        assert blocked["ready"] is False
        assert [g["key"] for g in blocked["groups"]] == ["undecided"]


def test_warnings_never_block_the_issue(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-warnings")
        with sqlite3.connect(db) as connection:
            record = connection.execute(
                "SELECT record_id FROM determinations WHERE assessment_id=? ORDER BY record_id",
                (assessment,),
            ).fetchone()[0]
        # Open corrective work: a Not Met with a reconciled action.
        client.put(
            f"/api/assessments/{assessment}/determinations/{record}",
            json={"status": "Not Met", "interview_observation": "Synthetic gap."},
        )
        reconciled = client.put(
            f"/api/projects/{project}/assessments/{assessment}/records/{record}/reconciliation",
            json={
                "outcome": "create",
                "title": "Synthetic finding",
                "action_title": "Synthetic corrective action",
                "rationale": "Synthetic gap needs remediation.",
            },
        )
        assert reconciled.status_code in (200, 201), reconciled.text
        # Evidence that is close to its review date.
        uploaded = client.post(
            f"/api/projects/{project}/evidence",
            files={"file": ("policy.txt", b"synthetic policy", "text/plain")},
        ).json()["id"]
        mapped = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={
                "artifact_id": uploaded,
                "record_id": "164.308(a)(1)(ii)(A)",
                "rationale": "Synthetic policy evidence.",
            },
        )
        assert mapped.status_code == 201, mapped.text
        soon = (datetime.now(UTC) + timedelta(days=5)).date().isoformat()
        review = client.put(
            f"/api/projects/{project}/evidence/{uploaded}/review-date",
            json={"review_date": soon},
        )
        assert review.status_code == 200, review.text

        checklist = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        ).json()
        assert checklist["ready"] is True and checklist["groups"] == []
        warnings = {w["key"]: w for w in checklist["warnings"]}
        assert warnings["open_corrective_work"]["count"] == 1
        assert warnings["open_corrective_work"]["target"] == "poam"
        assert warnings["evidence_due_soon"]["count"] == 1
        assert warnings["evidence_due_soon"]["target"] == "evidence"
        # Recorded Profile unknowns are not a warning: they are a hard gate (next test).
        assert "profile_follow_up" not in warnings

        # Nothing needs ticking: the act goes ahead with every warning showing.
        issued = _issue(client, project, assessment, "Issued with open corrective work.")
        assert issued.status_code == 201, issued.text


def _audit_details(db: Path, action: str) -> list[dict[str, Any]]:
    import json

    with sqlite3.connect(db) as connection:
        return [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT details_json FROM audit_events WHERE action=? ORDER BY rowid", (action,)
            )
        ]


def test_an_unusable_backup_folder_is_a_recorded_409_not_a_500(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-folder")
        backups = files / "backups"
        if backups.exists():
            import shutil

            shutil.rmtree(backups)
        backups.write_text("this is a file where the backup folder should be")
        failed = _issue(client, project, assessment)
        assert failed.status_code == 409, failed.text
        assert failed.json()["detail"].startswith("Backup failed: ")
        assert failed.json()["detail"].endswith("Nothing was issued.")
        assert _count(db, "issuance_snapshots") == 0
        assert _count(db, "backup_records", "status='failed'") == 1
        for action in ("package.backup_failed", "package.issue_failed"):
            details = _audit_details(db, action)
            assert len(details) == 1, action
            assert details[0]["stage"] == "backup" and details[0]["reason"]


def test_a_database_error_at_the_issue_step_is_audited_and_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance

    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-locked")

        def locked(*_a: object, **_k: object) -> None:
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(issuance, "issue_package", locked)
        failed = _issue(client, project, assessment)
        assert failed.status_code == 409, failed.text
        assert "Nothing was issued" in failed.json()["detail"]
        assert "database is locked" in failed.json()["detail"]
        assert _count(db, "issuance_snapshots") == 0
        details = _audit_details(db, "package.issue_failed")
        assert details[-1]["stage"] == "issue"
        assert "database is locked" in details[-1]["reason"]


def test_a_failed_generation_keeps_its_failed_attempt_and_the_real_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.generation as generation

    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-generation")

        def boom(*_a: object, **_k: object) -> str:
            raise RuntimeError("template exploded")

        monkeypatch.setattr(generation, "render_report", boom)
        failed = _issue(client, project, assessment)
        assert failed.status_code == 500, failed.text
        assert "Nothing was issued" in failed.json()["detail"]
    with sqlite3.connect(db) as connection:
        attempts = connection.execute("SELECT state, error FROM generation_attempts").fetchall()
    assert [state for state, _ in attempts] == ["failed"]
    assert "template exploded" in attempts[0][1]
    assert _count(db, "generated_packages") == 0
    details = _audit_details(db, "package.issue_failed")
    assert "template exploded" in details[-1]["reason"] and details[-1]["stage"] == "package"


def test_the_sign_off_text_does_not_claim_the_issue_happened_yet(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-text")
        assert _issue(client, project, assessment).status_code == 201
    with sqlite3.connect(db) as connection:
        approval = connection.execute("SELECT approval FROM package_review_events").fetchone()[0]
    assert approval.startswith("Reviewed for issue by Johnathan on ")


def test_a_double_submit_is_refused_clearly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance

    monkeypatch.setattr(issuance, "DOUBLE_SUBMIT_SECONDS", 60)
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-double")
        assert _issue(client, project, assessment).status_code == 201
        again = _issue(client, project, assessment)
        assert again.status_code == 409
        assert "just issued" in again.json()["detail"]
    assert _count(db, "issuance_snapshots") == 1
    assert _count(db, "generated_packages") == 1


def test_recorded_profile_unknowns_block_the_issue_with_a_link_to_the_profile(
    tmp_path: Path,
) -> None:
    from api.tests.test_issue_62_versioned_profile import profile_payload

    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "act-unknowns")
        base = client.get(f"/api/projects/{project}/profile").json()["active_version_id"]
        created = client.post(
            f"/api/projects/{project}/profile/versions", json={"base_version_id": base}
        ).json()
        saved = client.put(
            f"/api/projects/{project}/profile/versions/{created['id']}",
            json=profile_payload(created["content_revision"]),
        )
        assert saved.status_code == 200, saved.text
        approved = client.post(
            f"/api/projects/{project}/profile/versions/{created['id']}/lifecycle",
            json={"status": "Approved", "expected_revision": saved.json()["content_revision"]},
        )
        assert approved.status_code == 201, approved.text
        assert approved.json()["profile_complete"] is False
        checklist = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        ).json()
        groups = {g["key"]: g for g in checklist["groups"]}
        assert checklist["ready"] is False
        assert groups["profile_unknowns"]["label"] == "Profile unknowns to resolve"
        assert groups["profile_unknowns"]["target"] == "profile"
        assert "profile_follow_up" not in {w["key"] for w in checklist["warnings"]}
        refused = _issue(client, project, assessment)
        assert refused.status_code == 409
        assert "profile_unknowns" in {g["key"] for g in refused.json()["detail"]["groups"]}
    assert _count(db, "issuance_snapshots") == 0
