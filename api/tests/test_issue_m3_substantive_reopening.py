"""Substantive reopening, revalidation, and reissue (Issue #81)."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_issue_m3_assessment_revision_contract import migration_config
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app, _backup
from api.tests.test_issue_m3_hipaa_review import _package
from api.tests.test_issue_m3_presentation_correction import (
    IMMUTABLE_TABLES,
    _current,
    _dump,
    _issue,
    _sign,
)

PROJECT_WORK = ("findings", "corrective_actions", "risks", "evidence_versions")


def _issued_with_not_met(client: TestClient, db: Path, suffix: str) -> tuple[str, str, str, str]:
    project, assessment = _ready(client, db, suffix)
    with sqlite3.connect(db) as connection:
        record = connection.execute(
            "SELECT record_id FROM determinations WHERE assessment_id=? ORDER BY record_id",
            (assessment,),
        ).fetchone()[0]
    assert (
        client.put(
            f"/api/assessments/{assessment}/determinations/{record}",
            json={"status": "Not Met", "interview_observation": "Synthetic gap."},
        ).status_code
        == 200
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
    package = _package(client, project, assessment)
    _sign(client, project, package["id"])
    assert _issue(client, project, package["id"]).status_code == 201
    return project, assessment, package["id"], record


def _reopen(client: TestClient, project: str, package_id: str, **changes: Any) -> Response:
    payload: dict[str, Any] = {
        "actor_id": "johnathan",
        "classification": "substantive",
        "affected_record_ids": changes.pop("affected", []),
        "rationale": "Determination was based on superseded evidence.",
        **changes,
    }
    return client.post(f"/api/projects/{project}/packages/{package_id}/reopen", json=payload)


def _rows(db: Path, sql: str, *args: Any) -> list[tuple[Any, ...]]:
    with sqlite3.connect(db) as connection:
        return connection.execute(sql, args).fetchall()


def test_reopen_revalidate_regenerate_and_reissue(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, prior_assessment, prior, not_met = _issued_with_not_met(client, db, "reopen")
        affected = _rows(
            db,
            "SELECT record_id FROM determinations WHERE assessment_id=? AND status='Met' LIMIT 1",
            prior_assessment,
        )[0][0]
        work_before = _dump(db, PROJECT_WORK)
        immutable_before = _dump(db, IMMUTABLE_TABLES)
        prior_determinations = _rows(
            db, "SELECT * FROM determinations WHERE assessment_id=?", prior_assessment
        )

        reopened = _reopen(client, project, prior, affected=[affected])
        assert reopened.status_code == 201, reopened.text
        body = reopened.json()
        successor = body["successor_assessment_id"]
        reopening = body["reopening"]
        assert reopening["actor_id"] == "johnathan"
        assert reopening["predecessor_assessment_id"] == prior_assessment
        assert json.loads(reopening["affected_record_ids_json"]) == [affected]
        assert [item["record_id"] for item in body["revalidation_items"]] == [affected]
        assert client.get(f"/api/projects/{project}/assessment").json()["id"] == successor

        # Assessment-scoped state is copied; project work keeps its IDs and is not duplicated.
        copied = _rows(db, "SELECT * FROM determinations WHERE assessment_id=?", successor)
        assert sorted(row[1:] for row in copied) == sorted(row[1:] for row in prior_determinations)
        reconciliations = _rows(
            db,
            """SELECT assessment_id, id, finding_id, corrective_action_id
               FROM not_met_reconciliations WHERE record_id=? ORDER BY assessment_id""",
            not_met,
        )
        assert len(reconciliations) == 2
        assert {row[0] for row in reconciliations} == {prior_assessment, successor}
        assert reconciliations[0][1] != reconciliations[1][1]
        assert reconciliations[0][2:] == reconciliations[1][2:]
        assert _dump(db, PROJECT_WORK) == work_before
        assert _dump(db, IMMUTABLE_TABLES) == immutable_before
        assert _current(db, project) == [prior]

        # The affected record blocks close and generation until it is revalidated.
        readiness = client.get(
            f"/api/projects/{project}/assessments/{successor}/close-readiness"
        ).json()
        assert readiness["ready"] is False
        assert any("Revalidate reopened record" in str(b) for b in readiness["blockers"])
        blocked = client.post(f"/api/projects/{project}/assessments/{successor}/packages")
        assert blocked.status_code == 409
        detail = client.get(
            f"/api/projects/{project}/assessments/{successor}/records/{affected}"
        ).json()
        assert detail["revalidation"]["revalidated_by"] is None

        revalidated = client.post(
            f"/api/projects/{project}/assessments/{successor}/records/{affected}/revalidate",
            json={"actor_id": "johnathan", "note": "Re-examined with current evidence."},
        )
        assert revalidated.status_code == 201, revalidated.text
        again = client.post(
            f"/api/projects/{project}/assessments/{successor}/records/{affected}/revalidate",
            json={"actor_id": "johnathan", "note": "Twice."},
        )
        assert again.status_code == 409

        # A fresh package needs its own review; the prior sign-off cannot authorize it.
        package = _package(client, project, successor)
        assert package["assessment_id"] == successor
        assert _backup(client, project, package["id"]).status_code == 409
        assert _current(db, project) == [prior]
        _sign(client, project, package["id"])
        issued = _issue(client, project, package["id"])
        assert issued.status_code == 201, issued.text
        assert issued.json()["issuance_status"] == "Current"
        assert _current(db, project) == [package["id"]]

        listed = {
            item["id"]: item for item in client.get(f"/api/projects/{project}/packages").json()
        }
        assert listed[prior]["issuance_status"] == "Superseded"
        assert listed[prior]["superseded_by_package_id"] == package["id"]
        assert listed[prior]["reopening"]["successor_assessment_id"] == successor
        for component in listed[prior]["components"]:
            download = client.get(
                f"/api/projects/{project}/packages/{prior}/components/{component['id']}"
            )
            assert download.status_code == 200
            assert download.content == (files / component["relative_path"]).read_bytes()
        after = _dump(db, IMMUTABLE_TABLES)
        for table, rows in immutable_before.items():
            assert set(rows) <= set(after[table]), table

    with TestClient(create_app(database_path=db, storage_path=files)) as restarted:
        assert restarted.get(f"/api/projects/{project}/assessment").json()["id"] == successor
    assert _current(db, project) == [package["id"]]


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({"classification": "presentation_only"}, 409),
        ({"affected": []}, 422),
        ({"affected": ["not-a-record"]}, 409),
        ({"rationale": "   "}, 409),
    ],
)
def test_reopen_requires_explicit_classification_rationale_and_known_records(
    tmp_path: Path, changes: dict[str, Any], status: int
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, prior, record = _issued_with_not_met(client, db, "explicit")
        changes.setdefault("affected", [record])
        before = _dump(db, ("assessments", "assessment_reopenings", "determinations"))
        assert _reopen(client, project, prior, **changes).status_code == status
        assert _dump(db, ("assessments", "assessment_reopenings", "determinations")) == before
        assert client.get(f"/api/projects/{project}/assessment").json()["id"] == assessment


def test_retry_and_cross_project_reopen_create_nothing(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior, record = _issued_with_not_met(client, db, "retry-a")
        other, other_assessment, other_prior, _ = _issued_with_not_met(client, db, "retry-b")
        assert _reopen(client, other, prior, affected=[record]).status_code == 404
        assert _reopen(client, project, "guessed", affected=[record]).status_code == 404
        first = _reopen(client, project, prior, affected=[record])
        assert first.status_code == 201
        successor = first.json()["successor_assessment_id"]
        counts = _dump(db, ("assessments", "determinations", "findings", "corrective_actions"))
        assert _reopen(client, project, prior, affected=[record]).status_code in (404, 409)
        assert (
            _dump(db, ("assessments", "determinations", "findings", "corrective_actions")) == counts
        )
        assert (
            client.post(
                f"/api/projects/{other}/assessments/{successor}/records/{record}/revalidate",
                json={"actor_id": "johnathan", "note": "Cross project."},
            ).status_code
            == 404
        )
        assert client.get(f"/api/projects/{other}/assessment").json()["id"] == other_assessment
        assert _current(db, other) == [other_prior]
        # The pre-reopening package can no longer be presentation-corrected.
        assert (
            client.post(
                f"/api/projects/{project}/packages/{prior}/corrections",
                json={
                    "classification": "presentation_only",
                    "unchanged_source_attested": True,
                    "reason": "Stale.",
                },
            ).status_code
            == 404
        )


def test_direct_sql_cannot_rewrite_reopening_or_revalidation(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, prior, record = _issued_with_not_met(client, db, "direct")
        successor = _reopen(client, project, prior, affected=[record]).json()[
            "successor_assessment_id"
        ]
    with sqlite3.connect(db) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE assessment_reopenings SET rationale='x'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM assessment_reopenings")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM revalidation_items")
        with pytest.raises(sqlite3.IntegrityError, match="invalid revalidation item"):
            connection.execute(
                """INSERT INTO revalidation_items(id, project_id, reopening_id, assessment_id,
                   record_id) SELECT 'forged', project_id, reopening_id, assessment_id,
                   'not-affected' FROM revalidation_items"""
            )
        connection.execute(
            """UPDATE revalidation_items SET revalidated_by='johnathan',
               revalidated_at='t', note='ok'"""
        )
        with pytest.raises(sqlite3.IntegrityError, match="resolved once"):
            connection.execute("UPDATE revalidation_items SET note='changed'")
        issued = connection.execute("SELECT * FROM issuance_snapshots").fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="one current issued package"):
            # A second issue for the predecessor itself is not a reissue.
            connection.execute(
                "INSERT INTO issuance_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("forged", project, assessment, *issued[3:]),
            )
    assert successor


def test_migration_cycle_refuses_downgrade_with_reopenings(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior, record = _issued_with_not_met(client, db, "migrate")
    config = migration_config(db)
    command.downgrade(config, "-1")
    command.upgrade(config, "head")
    with client:
        assert _reopen(client, project, prior, affected=[record]).status_code == 201
    with pytest.raises(RuntimeError, match="downgrade would lose issued history"):
        command.downgrade(config, "-1")


def test_corrective_action_stays_tied_to_one_record_across_revisions(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior, record = _issued_with_not_met(client, db, "one-record")
        assert _reopen(client, project, prior, affected=[record]).status_code == 201
    with sqlite3.connect(db) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        rows = connection.execute(
            "SELECT * FROM not_met_reconciliations WHERE record_id=? ORDER BY assessment_id",
            (record,),
        ).fetchall()
        assert len(rows) == 2 and rows[0][6] == rows[1][6]
        other = connection.execute(
            "SELECT record_id FROM determinations WHERE record_id != ? LIMIT 1", (record,)
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="belongs to one record"):
            connection.execute(
                "UPDATE not_met_reconciliations SET record_id=? WHERE id=?", (other, rows[1][0])
            )
