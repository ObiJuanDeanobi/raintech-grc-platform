"""Migration 0022: one review-and-issue act, Profile approved once (GitHub issue #145).

Only two append-only guards change; no row is rewritten. A package left at
``In Review`` by the earlier chain stays as it is, reads as Draft, and can be
issued in one act. Downgrade restores the earlier guards.
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from api.database import configure_connection
from api.main import create_app
from api.package_review import _binding
from api.tests.test_issue_62_versioned_profile import create_project, profile_payload
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_review import _package

ROOT = Path(__file__).resolve().parents[2]
GUARDS = ("package_review_events_transition_guard", "profile_lifecycle_must_be_ordered")


def _config(database: Path, files: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(files))
    return config


def _guard_sql(database: Path) -> dict[str, str]:
    with sqlite3.connect(database) as connection:
        return {
            name: re.sub(r"\s+", " ", sql)
            for name, sql in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND name IN (?, ?)",
                GUARDS,
            )
        }


def _snapshot(database: Path) -> dict[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(database) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "AND name != 'alembic_version'"
            )
        ]
        return {
            table: sorted(connection.execute(f"SELECT * FROM {table}").fetchall(), key=repr)
            for table in tables
        }


def _in_review_event(database: Path, files: Path, package_id: str) -> None:
    """A 0021-era event: the earlier chain's first step, with role, note and confirmations."""
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        configure_connection(connection)
        package = connection.execute(
            "SELECT * FROM generated_packages WHERE id=?", (package_id,)
        ).fetchone()
        binding = _binding(connection, package, ROOT, files)
        assert not binding["blockers"] and not binding["drift"]
        connection.execute(
            """INSERT INTO package_review_events(
               id, project_id, assessment_id, package_id, sequence, prior_state, next_state,
               actor_id, reviewer_name, reviewer_role, note, approval, confirmations_json,
               package_sha256, source_snapshot_id, source_snapshot_sha256, template_version,
               component_ids_json, component_hashes_json, template_hashes_json,
               close_decision_json, created_at)
               VALUES (?,?,?,?,1,'Complete candidate','In Review','johnathan','Johnathan',
                       'Security Assessor','Started the review.','','{}',?,?,?,?,?,?,?,?,
                       '2026-10-01T00:00:00+00:00')""",
            (
                "legacy-in-review",
                package["project_id"],
                package["assessment_id"],
                package_id,
                binding["package_sha256"],
                binding["source_snapshot_id"],
                binding["source_snapshot_sha256"],
                binding["template_version"],
                json.dumps(binding["component_ids"], sort_keys=True),
                json.dumps(binding["component_hashes"], sort_keys=True),
                json.dumps(binding["template_hashes"], sort_keys=True),
                json.dumps(binding["close_decision"], sort_keys=True),
            ),
        )


def test_upgrade_lists_an_in_review_package_as_draft_and_it_issues_in_one_act(
    tmp_path: Path,
) -> None:
    database, files = tmp_path / "workspace.db", tmp_path / "files"
    config = _config(database, files)
    with TestClient(create_app(database_path=database, storage_path=files)) as client:
        project, assessment = _ready(client, database, "legacy")
        legacy = _package(client, project, assessment)["id"]

    # Back to the 0021 schema, where the earlier chain wrote its first step.
    command.downgrade(config, "0021")
    _in_review_event(database, files, legacy)
    before = _snapshot(database)
    command.upgrade(config, "head")

    # No row was rewritten or removed by the upgrade.
    after = _snapshot(database)
    for table, rows in before.items():
        assert set(rows) <= set(after[table]), table
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0022"

    with TestClient(create_app(database_path=database, storage_path=files)) as client:
        listed = client.get(f"/api/projects/{project}/packages").json()
        assert [(p["id"], p["lifecycle"]) for p in listed] == [(legacy, "Draft")]
        assert (
            client.get(f"/api/projects/{project}/packages/{legacy}/review").json()["state"]
            == "In Review"
        )
        # It can go straight to sign-off from In Review, and the act issues in one call.
        signed = client.post(
            f"/api/projects/{project}/packages/{legacy}/review/sign-off",
            json={"actor_id": "johnathan", "note": "Picked up after the upgrade."},
        )
        assert signed.status_code == 201, signed.text
        assert [e["next_state"] for e in signed.json()["events"]] == ["In Review", "Ready to issue"]
        assert signed.json()["events"][-1]["prior_state"] == "In Review"
        issued = client.post(
            f"/api/projects/{project}/assessments/{assessment}/issue",
            json={"actor_id": "johnathan", "note": "One act."},
        )
        assert issued.status_code == 201, issued.text
        lifecycles = {
            p["id"]: p["lifecycle"] for p in client.get(f"/api/projects/{project}/packages").json()
        }
        assert lifecycles[legacy] == "Draft"
        assert lifecycles[issued.json()["package_id"]] == "Issued"


def test_downgrade_restores_the_earlier_guards_exactly(tmp_path: Path) -> None:
    database, files = tmp_path / "workspace.db", tmp_path / "files"
    config = _config(database, files)
    command.upgrade(config, "0021")
    earlier = _guard_sql(database)
    command.upgrade(config, "head")
    newer = _guard_sql(database)
    assert set(earlier) == set(newer) == set(GUARDS)
    assert earlier != newer
    command.downgrade(config, "0021")
    assert _guard_sql(database) == earlier
    command.upgrade(config, "head")
    assert _guard_sql(database) == newer


def test_new_rules_allow_one_step_and_draft_to_approved_and_old_rules_do_not(
    tmp_path: Path,
) -> None:
    database, files = tmp_path / "workspace.db", tmp_path / "files"
    config = _config(database, files)
    with TestClient(create_app(database_path=database, storage_path=files)) as client:
        project = create_project(client, "guards")
        version = client.get(f"/api/projects/{project}/profile").json()["versions"][0]
        revision = version["content_revision"]
        saved = client.put(
            f"/api/projects/{project}/profile/versions/{version['id']}",
            json=profile_payload(revision),
        )
        assert saved.status_code == 200
        current = saved.json()["content_revision"]

    def approve_directly() -> None:
        with sqlite3.connect(database) as connection:
            configure_connection(connection)
            connection.execute(
                """INSERT INTO profile_lifecycle_events(
                   id, profile_version_id, status, actor_id, reviewer, content_revision,
                   created_at) VALUES ('direct', ?, 'Approved', 'johnathan', 'Johnathan', ?,
                   '2026-10-01T00:00:00+00:00')""",
                (version["id"], current),
            )

    command.downgrade(config, "0021")
    with pytest.raises(sqlite3.IntegrityError, match="Draft to Reviewed to Approved"):
        approve_directly()
    command.upgrade(config, "head")
    approve_directly()  # Draft goes straight to Approved
    with sqlite3.connect(database) as connection:
        statuses = [
            row[0]
            for row in connection.execute(
                "SELECT status FROM profile_lifecycle_events WHERE profile_version_id=? "
                "ORDER BY rowid",
                (version["id"],),
            )
        ]
    assert statuses == ["Draft", "Approved"]
    # The history is still append-only.
    with (
        sqlite3.connect(database) as connection,
        pytest.raises(sqlite3.IntegrityError, match="append-only"),
    ):
        connection.execute("UPDATE profile_lifecycle_events SET reviewer='forged'")
