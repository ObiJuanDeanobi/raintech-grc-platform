import sqlite3
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from api.main import create_app


def migration_config(database_path: Path, storage_path: Path) -> Config:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(storage_path))
    return config


def foreign_key_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_project(client: TestClient, client_id: str, name: str) -> str:
    return cast(
        str,
        client.post(
            f"/api/clients/{client_id}/projects",
            json={"name": name},
        ).json()["id"],
    )


def create_assessment(client: TestClient, project_id: str) -> str:
    assert (
        client.post(f"/api/projects/{project_id}/profile-readiness/acknowledgement").status_code
        == 201
    )
    assert (
        client.post(
            f"/api/projects/{project_id}/profile-readiness/transitions",
            json={
                "next_state": "Intake complete",
                "decision_note": "Synthetic test intake completed.",
            },
        ).status_code
        == 201
    )
    response = client.post(f"/api/projects/{project_id}/assessments")
    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "project_id",
        "framework_version_id",
        "created_at",
    }
    return cast(str, response.json()["id"])


def active_pointer(connection: sqlite3.Connection, project_id: str) -> tuple[str, str]:
    row = connection.execute(
        """
        SELECT project_id, assessment_id
        FROM project_active_assessments
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    assert row is not None
    return cast(tuple[str, str], row)


def test_clean_database_keeps_one_assessment_api_and_adds_one_active_revision(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)

    with TestClient(app) as client:
        client_id = client.post("/api/clients", json={"name": "Northwind Health"}).json()["id"]
        project_id = create_project(client, client_id, "HIPAA 2026")
        assert client.get(f"/api/projects/{project_id}/assessment").status_code == 404

        assessment_id = create_assessment(client, project_id)
        read = client.get(f"/api/projects/{project_id}/assessment")
        assert read.status_code == 200
        assert set(read.json()) == {
            "id",
            "project",
            "framework",
            "progress",
            "work_list",
            "record_index",
        }
        assert read.json()["id"] == assessment_id
        assert client.post(f"/api/projects/{project_id}/assessments").status_code == 409

    with foreign_key_connection(database_path) as connection:
        assert active_pointer(connection, project_id) == (project_id, assessment_id)
        assert connection.execute(
            """
            SELECT assessment_id, project_id, revision_number, predecessor_assessment_id
            FROM assessment_revisions
            WHERE assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone() == (assessment_id, project_id, 1, None)
        assert connection.execute(
            "SELECT COUNT(*) FROM project_active_assessments WHERE project_id = ?",
            (project_id,),
        ).fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError, match="assessments.project_id"):
            connection.execute(
                """
                INSERT INTO assessments(id, project_id, framework_version_id, created_at)
                VALUES ('forbidden-successor', ?, 'hipaa-45cfr164-2026-07-01',
                        '2026-08-27T00:00:00+00:00')
                """,
                (project_id,),
            )
        connection.rollback()
        assert active_pointer(connection, project_id) == (project_id, assessment_id)

    config = migration_config(database_path, storage_path)
    command.downgrade(config, "0005")
    with foreign_key_connection(database_path) as connection:
        assert connection.execute(
            "SELECT id, project_id FROM assessments WHERE id = ?",
            (assessment_id,),
        ).fetchone() == (assessment_id, project_id)
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name IN "
            "('assessment_revisions', 'project_active_assessments')"
        ).fetchone() == (0,)

    command.upgrade(config, "head")
    with foreign_key_connection(database_path) as connection:
        assert active_pointer(connection, project_id) == (project_id, assessment_id)
        assert connection.execute(
            """
            SELECT revision_number, predecessor_assessment_id
            FROM assessment_revisions
            WHERE assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone() == (1, None)


def test_populated_upgrade_downgrade_reupgrade_preserves_ids_data_and_pointer(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    config = migration_config(database_path, tmp_path / "files")
    command.upgrade(config, "0005")
    with foreign_key_connection(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO user_accounts(id, display_name) VALUES ('johnathan', 'Johnathan');
            INSERT INTO framework_versions(
                id, name, record_count, prompt_count, declarations_json
            ) VALUES ('framework-existing', 'Synthetic', 0, 0, '{}');
            INSERT INTO clients(id, name, created_at)
            VALUES ('client-existing', 'Existing Client', '2026-08-27T00:00:00+00:00');
            INSERT INTO projects(id, client_id, name, framework_version_id, created_at)
            VALUES (
                'project-existing', 'client-existing', 'Existing Project',
                'framework-existing', '2026-08-27T00:00:00+00:00'
            );
            INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES (
                'assessment-existing', 'project-existing', 'framework-existing',
                '2026-08-27T00:01:00+00:00'
            );
            INSERT INTO determinations(assessment_id, record_id, status, updated_at)
            VALUES (
                'assessment-existing', 'record-existing', 'Pending',
                '2026-08-27T00:02:00+00:00'
            );
            """
        )

    command.upgrade(config, "head")
    with foreign_key_connection(database_path) as connection:
        assert connection.execute(
            "SELECT id, project_id FROM assessments"
        ).fetchall() == [("assessment-existing", "project-existing")]
        assert connection.execute(
            "SELECT status FROM determinations WHERE assessment_id = 'assessment-existing'"
        ).fetchone() == ("Pending",)
        assert active_pointer(connection, "project-existing") == (
            "project-existing",
            "assessment-existing",
        )
        assert connection.execute(
            "SELECT revision_number, predecessor_assessment_id "
            "FROM assessment_revisions WHERE assessment_id = 'assessment-existing'"
        ).fetchone() == (1, None)

    command.downgrade(config, "0005")
    with foreign_key_connection(database_path) as connection:
        assert connection.execute(
            "SELECT id, project_id FROM assessments"
        ).fetchall() == [("assessment-existing", "project-existing")]
        assert connection.execute(
            "SELECT status FROM determinations WHERE assessment_id = 'assessment-existing'"
        ).fetchone() == ("Pending",)

    command.upgrade(config, "head")
    with foreign_key_connection(database_path) as connection:
        assert active_pointer(connection, "project-existing") == (
            "project-existing",
            "assessment-existing",
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM assessment_revisions"
        ).fetchone() == (1,)


def test_composite_constraints_reject_cross_project_pointer_and_chain_without_mutation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_a = client.post("/api/clients", json={"name": "Client A"}).json()["id"]
        client_b = client.post("/api/clients", json={"name": "Client B"}).json()["id"]
        project_a = create_project(client, client_a, "A")
        project_b = create_project(client, client_b, "B")
        assessment_a = create_assessment(client, project_a)
        assessment_b = create_assessment(client, project_b)

    with foreign_key_connection(database_path) as connection:
        before = {
            project_a: active_pointer(connection, project_a),
            project_b: active_pointer(connection, project_b),
        }
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                """
                UPDATE project_active_assessments
                SET assessment_id = ?
                WHERE project_id = ?
                """,
                (assessment_b, project_a),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                """
                UPDATE assessment_revisions
                SET predecessor_assessment_id = ?
                WHERE assessment_id = ?
                """,
                (assessment_b, assessment_a),
            )
        connection.rollback()
        assert active_pointer(connection, project_a) == before[project_a]
        assert active_pointer(connection, project_b) == before[project_b]
        assert connection.execute(
            "SELECT predecessor_assessment_id FROM assessment_revisions "
            "WHERE assessment_id = ?",
            (assessment_a,),
        ).fetchone() == (None,)
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            connection.execute(
                "DELETE FROM project_active_assessments WHERE project_id = ?",
                (project_a,),
            )
        connection.rollback()
        assert active_pointer(connection, project_a) == before[project_a]


@pytest.mark.parametrize("same_client", [True, False])
def test_guessed_assessment_ids_are_rejected_without_changing_active_pointer(
    tmp_path: Path,
    same_client: bool,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        client_a = client.post("/api/clients", json={"name": "Client A"}).json()["id"]
        client_b = (
            client_a
            if same_client
            else client.post("/api/clients", json={"name": "Client B"}).json()["id"]
        )
        project_a = create_project(client, client_a, "A")
        project_b = create_project(client, client_b, "B")
        assessment_a = create_assessment(client, project_a)
        assessment_b = create_assessment(client, project_b)

        assert (
            client.get(
                f"/api/projects/{project_b}/assessments/{assessment_a}"
                "/records/164.308(a)(1)(ii)(A)"
            ).status_code
            == 404
        )
        rejected = client.post(
            f"/api/projects/{project_b}/assessments/{assessment_a}/evidence-mappings",
            json={
                "artifact_id": "guessed-artifact",
                "record_id": "164.308(a)(1)(ii)(A)",
                "rationale": "Must not mutate another project.",
            },
        )
        assert rejected.status_code == 404

    with foreign_key_connection(database_path) as connection:
        assert active_pointer(connection, project_a) == (project_a, assessment_a)
        assert active_pointer(connection, project_b) == (project_b, assessment_b)
        assert connection.execute(
            "SELECT COUNT(*) FROM evidence_mappings"
        ).fetchone() == (0,)
