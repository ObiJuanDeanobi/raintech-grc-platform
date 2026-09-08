import json
import sqlite3
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_issue_m3_hipaa_sra import _risk, _setup


def project(client: TestClient, name: str) -> str:
    cid = client.post("/api/clients", json={"name": name}).json()["id"]
    return cast(
        str,
        client.post(f"/api/clients/{cid}/projects", json={"name": name}).json()["id"],
    )


def close(client: TestClient, project_id: str) -> Response:
    return client.get(f"/api/projects/{project_id}/close-readiness/fieldwork_ready_for_generation")


def test_unknown_profile_and_incomplete_profile_are_blockers(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as client:
        pid = project(client, "unknown")
        response = close(client, pid)
        assert response.status_code == 200
        codes = {item["code"] for item in response.json()["blockers"]}
        assert {"profile_not_complete", "profile_not_approved"} <= codes


def test_blank_pending_and_na_without_rationale_are_blockers(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as client:
        pid = project(client, "assessment")
        client.post(f"/api/projects/{pid}/profile-readiness/acknowledgement")
        client.post(
            f"/api/projects/{pid}/profile-readiness/transitions",
            json={"next_state": "Intake complete", "decision_note": "test"},
        )
        assessment = client.post(f"/api/projects/{pid}/assessments").json()
        body = close(client, pid).json()
        assert any(item["code"] == "determination_not_final" for item in body["blockers"])
        # The endpoint must not treat a missing/blank determination as complete.
        assert body["ready"] is False
        assert assessment["project_id"] == pid


def test_unknown_target_and_guessed_project_ids_are_rejected(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as client:
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
        assert [item["code"] for item in first["blockers"]] == [
            item["code"] for item in second["blockers"]
        ]
        assert all(one in item.get("link", "") for item in first["blockers"])
        assert all(two in item.get("link", "") for item in second["blockers"])
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT id FROM projects").fetchall()
        assert len(rows) == 2


def test_close_readiness_consumes_framework_declaration(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as client:
        pid = project(client, "altered")
        with sqlite3.connect(db) as connection:
            framework_id = connection.execute(
                "SELECT framework_version_id FROM projects WHERE id=?", (pid,)
            ).fetchone()[0]
            declarations = json.loads(
                connection.execute(
                    "SELECT declarations_json FROM framework_versions WHERE id=?", (framework_id,)
                ).fetchone()[0]
            )
            declarations["profile_readiness"]["profile_completion"]["state"] = "Synthetic complete"
            connection.execute(
                "UPDATE framework_versions SET declarations_json=? WHERE id=?",
                (json.dumps(declarations), framework_id),
            )
            connection.commit()
        result = close(client, pid).json()
        assert any(item["code"] == "profile_not_complete" for item in result["blockers"])


def test_assessment_id_is_scoped_to_project_and_response_has_actionable_shape(
    tmp_path: Path,
) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as client:
        one = project(client, "one")
        two = project(client, "two")
        for pid in (one, two):
            client.post(f"/api/projects/{pid}/profile-readiness/acknowledgement")
            client.post(
                f"/api/projects/{pid}/profile-readiness/transitions",
                json={"next_state": "Intake complete", "decision_note": "test"},
            )
        assessment = client.post(f"/api/projects/{one}/assessments").json()["id"]
        wrong = client.get(f"/api/projects/{two}/assessments/{assessment}/close-readiness")
        assert wrong.status_code == 404
        body = client.get(f"/api/projects/{one}/assessments/{assessment}/close-readiness").json()
        assert {
            "target",
            "status",
            "ready",
            "checks",
            "blockers",
            "links",
            "informational",
        } <= body.keys()
        assert isinstance(body["links"], list)


def test_na_without_rationale_blocks_but_justified_na_is_not_a_na_blocker(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as client:
        pid = project(client, "na")
        client.post(f"/api/projects/{pid}/profile-readiness/acknowledgement")
        client.post(
            f"/api/projects/{pid}/profile-readiness/transitions",
            json={"next_state": "Intake complete", "decision_note": "test"},
        )
        aid = client.post(f"/api/projects/{pid}/assessments").json()["id"]
        record = "164.308(a)(1)(ii)(B)"
        assert (
            client.put(
                f"/api/assessments/{aid}/determinations/{record}", json={"status": "N/A"}
            ).status_code
            == 422
        )
        assert (
            client.put(
                f"/api/assessments/{aid}/determinations/{record}",
                json={
                    "status": "N/A",
                    "na_rationale": "Not applicable to this documented environment.",
                },
            ).status_code
            == 200
        )
        body = client.get(f"/api/projects/{pid}/assessments/{aid}/close-readiness").json()
        assert not any(item["code"] == "na_rationale_missing" for item in body["blockers"])


def test_sra_and_risk_review_are_explicit_close_checks(tmp_path: Path) -> None:
    with TestClient(
        create_app(database_path=tmp_path / "db.sqlite", storage_path=tmp_path / "files")
    ) as client:
        pid = project(client, "sra")
        body = close(client, pid).json()
        codes = {item["code"] for item in body["blockers"]}
        assert "sra_incomplete" in codes or "sra_not_approved" in codes
        assert "risk_incomplete" in codes or "risk_review_missing" in codes
        assert body["informational"]["package"] == "not_applicable"


def test_ready_without_package_and_reconciled_open_action_passes(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as client:
        pid, aid, profile = _setup(client, "close-ready")
        completed = client.post(
            f"/api/projects/{pid}/profile-readiness/transitions",
            json={
                "next_state": "Profile complete",
                "decision_note": "All Profile facts resolved.",
                "reviewed_by": "Reviewer",
                "approval_evidence": "Approved Profile lifecycle event.",
            },
        )
        assert completed.status_code == 201, completed.text
        scope = client.get(f"/api/projects/{pid}/sra").json()["scope_items"]
        assert scope
        for item in scope:
            reviewed = client.put(
                f"/api/projects/{pid}/sra/scope",
                json={
                    "profile_version_id": profile["id"],
                    "scope_type": item["scope_type"],
                    "target_key": item["target_key"],
                    "included": True,
                },
            )
            assert reviewed.status_code == 200, reviewed.text
        risk = client.post(f"/api/projects/{pid}/risks", json=_risk(profile["id"], aid))
        assert risk.status_code == 201, risk.text
        with sqlite3.connect(db) as connection:
            record_ids = [
                row[0]
                for row in connection.execute(
                    """SELECT record_id FROM framework_records
                       WHERE framework_version_id = (
                           SELECT framework_version_id FROM projects WHERE id = ?
                       )
                         AND carries_determination = 1""",
                    (pid,),
                )
            ]
            connection.executemany(
                """INSERT INTO determinations(assessment_id, record_id, status, updated_at)
                   VALUES (?, ?, 'Met', '2026-09-08T00:00:00+00:00')""",
                [(aid, record_id) for record_id in record_ids],
            )
            connection.commit()
        ready = client.get(f"/api/projects/{pid}/assessments/{aid}/close-readiness").json()
        assert ready["status"] == "Ready"
        assert ready["blockers"] == []
        assert ready["informational"] == {
            "package": "not_applicable",
            "review": "not_applicable",
            "sign": "not_applicable",
            "backup": "not_applicable",
            "snapshot": "not_applicable",
        }

        record_id = "164.308(a)(1)(ii)(B)"
        assert (
            client.put(
                f"/api/assessments/{aid}/determinations/{record_id}",
                json={"status": "Not Met"},
            ).status_code
            == 200
        )
        path = f"/api/projects/{pid}/assessments/{aid}/records/{record_id}/reconciliation"
        reconciled = client.put(
            path,
            json={"outcome": "create", "title": "Open finding", "action_title": "Open action"},
        )
        assert reconciled.status_code == 200, reconciled.text
        action_link = next(
            item for item in reconciled.json()["links"] if item["type"] == "corrective_action"
        )
        assert action_link["status"] != "Closed"
        still_ready = client.get(f"/api/projects/{pid}/assessments/{aid}/close-readiness").json()
        assert still_ready["status"] == "Ready"
