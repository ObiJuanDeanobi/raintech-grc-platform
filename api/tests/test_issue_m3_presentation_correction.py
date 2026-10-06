"""Presentation-only correction and governed reissue (Issue #80)."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_issue_m3_assessment_revision_contract import migration_config
from api.tests.test_issue_m3_hipaa_issue_backup import _app, _backup, _issued_candidate
from api.tests.test_issue_m3_hipaa_review import _transition

SOURCE_TABLES = (
    "assessments",
    "assessment_revisions",
    "determinations",
    "profile_versions",
    "profile_field_values",
    "evidence_versions",
    "findings",
    "corrective_actions",
    "risks",
    "not_met_reconciliations",
)
IMMUTABLE_TABLES = (
    "source_snapshots",
    "generated_packages",
    "generated_components",
    "package_review_events",
    "backup_records",
    "backup_items",
    "issuance_snapshots",
)


def _issue(client: TestClient, project: str, package_id: str) -> Response:
    backup = _backup(client, project, package_id)
    assert backup.status_code == 201, backup.text
    return client.post(
        f"/api/projects/{project}/packages/{package_id}/issue",
        json={"actor_id": "johnathan", "backup_id": backup.json()["id"]},
    )


def _issued(client: TestClient, db: Path, suffix: str) -> tuple[str, str, str]:
    project, assessment, package = _issued_candidate(client, db, suffix)
    issued = _issue(client, project, package["id"])
    assert issued.status_code == 201, issued.text
    return project, assessment, package["id"]


def _correct(client: TestClient, project: str, package_id: str, **changes: Any) -> Response:
    payload = {
        "actor_id": "johnathan",
        "classification": "presentation_only",
        "unchanged_source_attested": True,
        "reason": "Correct report cover formatting.",
        **changes,
    }
    return client.post(f"/api/projects/{project}/packages/{package_id}/corrections", json=payload)


def _sign(client: TestClient, project: str, package_id: str) -> None:
    for state in ("In Review", "Reviewed", "Ready to issue"):
        assert _transition(client, project, package_id, state).status_code == 201


def _dump(db: Path, tables: tuple[str, ...]) -> dict[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(db) as connection:
        return {
            table: sorted(connection.execute(f"SELECT * FROM {table}").fetchall())
            for table in tables
        }


def _current(db: Path, project: str) -> list[str]:
    with sqlite3.connect(db) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT package_id FROM current_issuances WHERE project_id=?", (project,)
            )
        ]


def test_correction_reissues_from_same_snapshot_and_supersedes_prior(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, _, prior = _issued(client, db, "correct")
        source_before = _dump(db, SOURCE_TABLES)
        immutable_before = _dump(db, IMMUTABLE_TABLES)

        created = _correct(client, project, prior)
        assert created.status_code == 201, created.text
        correction, package = created.json()["correction"], created.json()["package"]
        assert correction["classification"] == "presentation_only"
        assert correction["unchanged_source_attested"] == 1
        assert correction["actor_id"] == "johnathan"
        assert correction["reason"] == "Correct report cover formatting."
        assert correction["prior_package_id"] == prior
        assert correction["result_package_id"] == package["id"]

        # Reissue requires the full review, backup, and issue governance.
        blocked = client.get(f"/api/projects/{project}/packages/{package['id']}/issue-readiness")
        assert blocked.json()["pre_backup_issue_ready"] is False
        assert _backup(client, project, package["id"]).status_code == 409
        assert _current(db, project) == [prior]
        _sign(client, project, package["id"])
        issued = _issue(client, project, package["id"])
        assert issued.status_code == 201, issued.text
        assert issued.json()["issuance_status"] == "Current"

        assert _current(db, project) == [package["id"]]
        assert _dump(db, SOURCE_TABLES) == source_before
        after = _dump(db, IMMUTABLE_TABLES)
        for table, rows in immutable_before.items():
            assert set(rows) <= set(after[table]), table
        with sqlite3.connect(db) as connection:
            snapshots = connection.execute(
                "SELECT source_snapshot_id FROM generated_packages WHERE project_id=?",
                (project,),
            ).fetchall()
            assert len(set(snapshots)) == 1
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM source_snapshots WHERE project_id=?", (project,)
                ).fetchone()[0]
                == 1
            )

        listed = {
            item["id"]: item for item in client.get(f"/api/projects/{project}/packages").json()
        }
        assert listed[prior]["issuance_status"] == "Superseded"
        assert listed[prior]["superseded_by_package_id"] == package["id"]
        assert listed[package["id"]]["issuance_status"] == "Current"
        assert listed[package["id"]]["correction"]["prior_package_id"] == prior
        for component in listed[prior]["components"]:
            download = client.get(
                f"/api/projects/{project}/packages/{prior}/components/{component['id']}"
            )
            assert download.status_code == 200
            assert download.content == (files / component["relative_path"]).read_bytes()
        prior_readiness = client.get(f"/api/projects/{project}/packages/{prior}/issue-readiness")
        assert prior_readiness.json()["issuance_status"] == "Superseded"

    with TestClient(create_app(database_path=db, storage_path=files)) as restarted:
        listed = restarted.get(f"/api/projects/{project}/packages").json()
        assert [item["id"] for item in listed if item["issuance_status"] == "Current"] == [
            package["id"]
        ]
    assert _current(db, project) == [package["id"]]


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({"classification": "substantive"}, 409),
        ({"classification": ""}, 422),
        ({"unchanged_source_attested": False}, 409),
        ({"reason": "   "}, 409),
    ],
)
def test_classification_attestation_and_reason_are_explicit(
    tmp_path: Path, changes: dict[str, Any], status: int
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior = _issued(client, db, "explicit")
        before = _dump(db, IMMUTABLE_TABLES)
        assert _correct(client, project, prior, **changes).status_code == status
        missing = client.post(
            f"/api/projects/{project}/packages/{prior}/corrections",
            json={"actor_id": "johnathan", "reason": "No classification."},
        )
        assert missing.status_code == 422
        assert _dump(db, IMMUTABLE_TABLES) == before
        assert _dump(db, ("package_corrections",)) == {"package_corrections": []}


def test_changed_source_and_unissued_packages_cannot_be_presentation_corrected(
    tmp_path: Path,
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, candidate = _issued_candidate(client, db, "unissued")
        assert _correct(client, project, candidate["id"]).status_code == 409
        assert _issue(client, project, candidate["id"]).status_code == 201
        with sqlite3.connect(db) as connection:
            connection.execute(
                "UPDATE determinations SET interview_observation=? WHERE assessment_id=?",
                ("Changed after issue.", assessment),
            )
            connection.commit()
        changed = _correct(client, project, candidate["id"])
        assert changed.status_code == 409
        assert "presentation-only correction is not allowed" in changed.json()["detail"]
        assert _current(db, project) == [candidate["id"]]


def test_failed_reissue_leaves_current_issue_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance_module

    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior = _issued(client, db, "failed-reissue")
        package = _correct(client, project, prior).json()["package"]
        _sign(client, project, package["id"])
        monkeypatch.setattr(
            issuance_module,
            "_validate_archive",
            lambda *a, **k: (_ for _ in ()).throw(OSError("forced backup failure")),
        )
        assert _backup(client, project, package["id"]).status_code == 409
        failed = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": "missing"},
        )
        assert failed.status_code == 409
        assert _current(db, project) == [prior]
        assert _dump(db, ("issuance_supersessions",)) == {"issuance_supersessions": []}


def test_only_one_correction_can_supersede_and_uncorrected_packages_cannot_issue(
    tmp_path: Path,
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, prior = _issued(client, db, "stale")
        first = _correct(client, project, prior).json()["package"]["id"]
        second = _correct(client, project, prior).json()["package"]["id"]
        plain = client.post(f"/api/projects/{project}/assessments/{assessment}/packages").json()
        for package_id in (first, second, plain["id"]):
            _sign(client, project, package_id)
        assert _issue(client, project, first).status_code == 201

        readiness = client.get(f"/api/projects/{project}/packages/{second}/issue-readiness")
        assert "no longer the current issue" in " ".join(readiness.json()["blockers"])
        assert _backup(client, project, second).status_code == 409
        plain_readiness = client.get(
            f"/api/projects/{project}/packages/{plain['id']}/issue-readiness"
        )
        assert "current issued package already exists" in " ".join(
            plain_readiness.json()["blockers"]
        )
        # Correcting a superseded issue is stale and fails closed.
        assert _correct(client, project, prior).status_code == 409
        assert _current(db, project) == [first]


def test_corrections_are_project_scoped(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, _, prior = _issued(client, db, "scope-a")
        other, _, other_prior = _issued(client, db, "scope-b")
        assert _correct(client, other, prior).status_code == 404
        assert _correct(client, project, "guessed-package").status_code == 404
        assert _correct(client, "guessed-project", prior).status_code == 404
        package = _correct(client, project, prior).json()["package"]["id"]
        assert client.get(f"/api/projects/{other}/packages/{package}/review").status_code == 404
        assert package not in {
            item["id"] for item in client.get(f"/api/projects/{other}/packages").json()
        }
        assert _current(db, project) == [prior]
        assert _current(db, other) == [other_prior]


def test_direct_sql_cannot_forge_second_current_issue_or_rewrite_history(
    tmp_path: Path,
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, prior = _issued(client, db, "direct-sql")
        package = _correct(client, project, prior).json()["package"]["id"]
        _sign(client, project, package)
        _issue(client, project, package)
        plain = client.post(f"/api/projects/{project}/assessments/{assessment}/packages").json()
    with sqlite3.connect(db) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for table in ("package_corrections", "issuance_supersessions"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"UPDATE {table} SET actor_id='johnathan'")
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"DELETE FROM {table}")
        issued = connection.execute(
            "SELECT * FROM issuance_snapshots WHERE package_id=?", (package,)
        ).fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="one current issued package"):
            connection.execute(
                "INSERT INTO issuance_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("forged", project, assessment, plain["id"], *issued[4:]),
            )
        correction = connection.execute("SELECT * FROM package_corrections").fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="invalid presentation correction"):
            connection.execute(
                "INSERT INTO package_corrections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("forged", *correction[1:8], plain["id"], *correction[9:]),
            )
        with pytest.raises(sqlite3.IntegrityError, match="invalid issuance supersession"):
            connection.execute(
                "INSERT INTO issuance_supersessions VALUES (?,?,?,?,?,?,?,?)",
                ("forged", project, correction[0], correction[7], prior, plain["id"], "x", "t"),
            )


def test_migration_cycles_on_populated_database(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        _issued(client, db, "migrate")
    config = migration_config(db)
    command.downgrade(config, "0013")
    with sqlite3.connect(db) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name='package_corrections'"
        ).fetchone() is None
    command.upgrade(config, "head")
    with client:
        project = client.get("/api/clients").json()[0]["projects"][0]["id"]
        prior = _current(db, project)[0]
        assert _correct(client, project, prior).status_code == 201
    with pytest.raises(RuntimeError, match="downgrade would lose issued history"):
        command.downgrade(config, "0013")


def test_upgrade_refuses_projects_with_multiple_unsuperseded_issues(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment, _ = _issued(client, db, "legacy-double")
        plain = client.post(f"/api/projects/{project}/assessments/{assessment}/packages").json()
    config = migration_config(db)
    command.downgrade(config, "0013")
    with sqlite3.connect(db) as connection:
        # Pre-#80 schema did not stop a second first-issue; simulate that legacy row.
        connection.execute("DROP TRIGGER issuance_snapshots_insert_guard")
        issued = connection.execute("SELECT * FROM issuance_snapshots").fetchone()
        connection.execute(
            "INSERT INTO issuance_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("legacy", *issued[1:3], plain["id"], *issued[4:]),
        )
        connection.commit()
    with pytest.raises(RuntimeError, match="more than one issued package"):
        command.upgrade(config, "head")
