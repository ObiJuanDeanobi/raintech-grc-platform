import json
import sqlite3
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient

from api.database import Database
from api.framework import FRAMEWORK_ID, seed_framework
from api.main import create_app
from api.tests.test_workspace_api import (
    create_workspace,
    migration_config,
    record_path,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPOSITORY_ROOT / "catalog" / "versions" / f"{FRAMEWORK_ID}.json"
PROMPT_LAYER_PATH = (
    REPOSITORY_ROOT / "catalog" / "versions" / f"{FRAMEWORK_ID}-prompts.json"
)


def test_assessment_walkthrough_contains_every_catalog_record_in_stable_order(
    tmp_path: Path,
) -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    expected_ids = [record["id"] for record in catalog["records"]]
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")

    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        assessment = client.get(f"/api/projects/{project_id}/assessment").json()

        assert [record["record_id"] for record in assessment["work_list"]] == expected_ids
        assert len(assessment["work_list"]) == len(set(expected_ids))
        assert assessment["framework"]["walkthrough_record_count"] == len(expected_ids)
        assert assessment["framework"]["determination_record_count"] == 149
        assert assessment["progress"] == {
            "resolved_determination_count": 0,
            "determination_record_count": 149,
        }

        visited: list[str] = []
        next_record_id: str | None = expected_ids[0]
        while next_record_id is not None:
            assert next_record_id not in visited
            detail = client.get(
                record_path(project_id, assessment_id, next_record_id)
            ).json()
            visited.append(next_record_id)
            assert detail["position"]["current"] == len(visited)
            assert detail["position"]["total"] == len(expected_ids)
            assert detail["record"]["citation"]
            assert detail["record"]["regulation_text"]
            next_record_id = detail["position"]["next_record_id"]

        assert visited == expected_ids
        first = client.get(record_path(project_id, assessment_id, expected_ids[0])).json()
        last = client.get(record_path(project_id, assessment_id, expected_ids[-1])).json()
        assert first["position"]["previous_record_id"] is None
        assert last["position"]["next_record_id"] is None


def test_walkthrough_endpoints_consume_the_pinned_membership_declaration(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        first_record_id = client.get(
            f"/api/projects/{project_id}/assessment"
        ).json()["work_list"][0]["record_id"]
        with sqlite3.connect(database_path) as connection:
            declarations = json.loads(
                connection.execute(
                    "SELECT declarations_json FROM framework_versions WHERE id = ?",
                    (FRAMEWORK_ID,),
                ).fetchone()[0]
            )
            declarations["walkthrough_membership"] = "synthetic_unsupported_rule"
            connection.execute(
                "UPDATE framework_versions SET declarations_json = ? WHERE id = ?",
                (json.dumps(declarations), FRAMEWORK_ID),
            )

        try:
            client.get(f"/api/projects/{project_id}/assessment")
        except ValueError as error:
            assert str(error) == (
                "Unsupported walkthrough membership rule: synthetic_unsupported_rule"
            )
        else:
            raise AssertionError("work-list endpoint ignored walkthrough membership")

        try:
            client.get(record_path(project_id, assessment_id, first_record_id))
        except ValueError as error:
            assert str(error) == (
                "Unsupported walkthrough membership rule: synthetic_unsupported_rule"
            )
        else:
            raise AssertionError("record traversal ignored walkthrough membership")


def test_record_detail_preserves_prompt_layer_no_prompt_explanation_exactly(
    tmp_path: Path,
) -> None:
    layer = json.loads(PROMPT_LAYER_PATH.read_text(encoding="utf-8"))
    explanations = {
        item["record_id"]: item["reason"] for item in layer["records_without_prompts"]
    }
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")

    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        for record_id, expected in explanations.items():
            detail = client.get(record_path(project_id, assessment_id, record_id)).json()
            assert detail["prompts"] == []
            assert detail["no_prompt_explanation"] == expected

        prompted_id = next(iter(layer["entries"]))
        prompted = client.get(record_path(project_id, assessment_id, prompted_id)).json()
        assert prompted["prompts"]
        assert prompted["no_prompt_explanation"] is None


def test_progress_uses_only_resolved_determination_bearing_records(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)

    with sqlite3.connect(database_path) as connection:
        records = connection.execute(
            """
            SELECT record_id FROM framework_records
            WHERE framework_version_id = ? AND carries_determination = 1
            ORDER BY sort_order LIMIT 5
            """,
            (FRAMEWORK_ID,),
        ).fetchall()
        for (record_id,), status in zip(
            records, ("Met", "Not Met", "N/A", "Pending", ""), strict=True
        ):
            connection.execute(
                """
                INSERT INTO determinations(
                    assessment_id, record_id, status, updated_at
                ) VALUES (?, ?, ?, '2026-08-26T00:00:00+00:00')
                """,
                (assessment_id, record_id, status),
            )
        derived_parent = connection.execute(
            """
            SELECT record_id FROM framework_records
            WHERE framework_version_id = ? AND carries_determination = 0
            ORDER BY sort_order LIMIT 1
            """,
            (FRAMEWORK_ID,),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO determinations(
                assessment_id, record_id, status, updated_at
            ) VALUES (?, ?, 'Met', '2026-08-26T00:00:00+00:00')
            """,
            (assessment_id, derived_parent),
        )

    restarted = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(restarted) as client:
        assessment = client.get(f"/api/projects/{project_id}/assessment").json()
        assert assessment["progress"] == {
            "resolved_determination_count": 3,
            "determination_record_count": 149,
        }


def test_legacy_placement_history_is_inert_and_write_routes_are_unavailable(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        source_id = "164.308(a)(1)(i)"
        destination_id = "164.308(a)(7)(i)"
        source = client.get(record_path(project_id, assessment_id, source_id)).json()
        prompt = source["prompts"][0]

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO prompt_placements(
                assessment_id, prompt_id, placement_type, destination_record_id,
                rule_citation, reason, actor_id, created_at
            ) VALUES (?, ?, 'record', ?, '45 CFR synthetic', 'legacy reason',
                      'johnathan', '2026-08-25T12:00:00+00:00')
            """,
            (assessment_id, prompt["id"], destination_id),
        )
        connection.execute(
            """
            INSERT INTO prompt_move_rejections(
                assessment_id, prompt_id, proposed_record_id, reason, actor_id, created_at
            ) VALUES (?, ?, ?, 'legacy rejection', 'johnathan',
                      '2026-08-25T12:01:00+00:00')
            """,
            (assessment_id, prompt["id"], destination_id),
        )

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        source = client.get(record_path(project_id, assessment_id, source_id)).json()
        destination = client.get(record_path(project_id, assessment_id, destination_id)).json()
        assert any(item["id"] == prompt["id"] for item in source["prompts"])
        assert all(item["id"] != prompt["id"] for item in destination["prompts"])
        assert (
            client.put(
                f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/placement",
                json={"destination_record_id": destination_id, "reason": "new"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/rejections",
                json={"proposed_record_id": destination_id, "reason": "new"},
            ).status_code
            == 405
        )


def test_two_projects_keep_answers_isolated_and_ignore_historical_placements(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_a, assessment_a = create_workspace(client)
        project_b, assessment_b = create_workspace(client)
        source_id = "164.308(a)(1)(i)"
        destination_id = "164.308(a)(7)(i)"
        prompt = client.get(record_path(project_a, assessment_a, source_id)).json()["prompts"][0]
        for assessment_id, answer in (
            (assessment_a, "Project A answer"),
            (assessment_b, "Project B answer"),
        ):
            assert (
                client.put(
                    f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/answer",
                    json={"answer": answer},
                ).status_code
                == 200
            )

    with sqlite3.connect(database_path) as connection:
        for assessment_id, destination in (
            (assessment_a, destination_id),
            (assessment_b, source_id),
        ):
            connection.execute(
                """
                INSERT INTO prompt_placements(
                    assessment_id, prompt_id, placement_type, destination_record_id,
                    rule_citation, reason, actor_id, created_at
                ) VALUES (?, ?, 'record', ?, 'legacy', 'legacy', 'johnathan',
                          '2026-08-25T12:00:00+00:00')
                """,
                (assessment_id, prompt["id"], destination),
            )

    restarted = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(restarted) as client:
        detail_a = client.get(record_path(project_a, assessment_a, source_id)).json()
        detail_b = client.get(record_path(project_b, assessment_b, source_id)).json()
        answer_a = next(item for item in detail_a["prompts"] if item["id"] == prompt["id"])
        answer_b = next(item for item in detail_b["prompts"] if item["id"] == prompt["id"])
        assert answer_a["answer"] == "Project A answer"
        assert answer_b["answer"] == "Project B answer"
        assert client.get(record_path(project_a, assessment_b, source_id)).status_code == 404
        assert client.get(record_path(project_b, assessment_a, source_id)).status_code == 404


def test_populated_0002_upgrade_restart_and_migration_cycle_preserve_legacy_history(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    config = migration_config(database_path, storage_path)
    command.upgrade(config, "head")
    database = Database(database_path, storage_path)
    seed_framework(database, REPOSITORY_ROOT)
    command.downgrade(config, "0002")

    prompt_layer = json.loads(PROMPT_LAYER_PATH.read_text(encoding="utf-8"))
    prompt_record_id = next(iter(prompt_layer["entries"]))
    with sqlite3.connect(database_path) as connection:
        prompt_id = connection.execute(
            """
            SELECT prompt_id FROM framework_prompts
            WHERE original_record_id = ? ORDER BY sort_order LIMIT 1
            """,
            (prompt_record_id,),
        ).fetchone()[0]
        placement_destination = connection.execute(
            """
            SELECT record_id FROM framework_records
            WHERE framework_version_id = ? AND record_id != ?
            ORDER BY sort_order DESC LIMIT 1
            """,
            (FRAMEWORK_ID, prompt_record_id),
        ).fetchone()[0]
        connection.executescript(
            """
            INSERT INTO clients VALUES ('legacy-client', 'Legacy Client',
                '2026-08-25T00:00:00+00:00');
            INSERT INTO projects VALUES ('legacy-project', 'legacy-client', 'Legacy Project',
                'hipaa-45cfr164-2026-07-01', '2026-08-25T00:00:00+00:00');
            INSERT INTO assessments VALUES ('legacy-assessment', 'legacy-project',
                'hipaa-45cfr164-2026-07-01', '2026-08-25T00:00:00+00:00');
            """
        )
        connection.execute(
            """
            INSERT INTO prompt_answers VALUES (
                'legacy-assessment', ?, 'stable legacy answer',
                '2026-08-25T01:00:00+00:00')
            """,
            (prompt_id,),
        )
        for placement_type, destination, suffix in (
            ("record", placement_destination, "record"),
            ("context", None, "context"),
        ):
            other_prompt_id = prompt_id
            if suffix == "context":
                other_prompt_id = connection.execute(
                    "SELECT prompt_id FROM framework_prompts WHERE prompt_id != ? LIMIT 1",
                    (prompt_id,),
                ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO prompt_placements VALUES (
                    'legacy-assessment', ?, ?, ?, 'legacy citation', ?,
                    'johnathan', ?)
                """,
                (
                    other_prompt_id,
                    placement_type,
                    destination,
                    f"legacy {suffix}",
                    f"2026-08-25T02:00:0{len(suffix)}+00:00",
                ),
            )
        connection.execute(
            """
            INSERT INTO prompt_move_rejections VALUES (
                'legacy-assessment', ?, ?, 'legacy rejection', 'johnathan',
                '2026-08-25T03:00:00+00:00')
            """,
            (prompt_id, placement_destination),
        )
        connection.execute(
            """
            INSERT INTO audit_events VALUES (
                'legacy-audit', 'johnathan', 'legacy.event', 'prompt_placement',
                'legacy-entity', '{"stable":true}', '2026-08-25T04:00:00+00:00')
            """
        )
        before = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in (
                "prompt_answers",
                "prompt_placements",
                "prompt_move_rejections",
                "audit_events",
            )
        }

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        for table, rows in before.items():
            assert connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() == rows
        assert "no_prompt_explanation" in {
            row[1] for row in connection.execute("PRAGMA table_info(framework_records)")
        }

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        detail = client.get(
            record_path("legacy-project", "legacy-assessment", prompt_record_id)
        ).json()
        saved = next(item for item in detail["prompts"] if item["id"] == prompt_id)
        assert saved["answer"] == "stable legacy answer"
        destination = client.get(
            record_path("legacy-project", "legacy-assessment", placement_destination)
        ).json()
        assert all(item["id"] != prompt_id for item in destination["prompts"])
    with sqlite3.connect(database_path) as connection:
        explanation = connection.execute(
            """
            SELECT no_prompt_explanation FROM framework_records
            WHERE no_prompt_explanation IS NOT NULL LIMIT 1
            """
        ).fetchone()
        assert explanation and explanation[0]

    command.downgrade(config, "0002")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(framework_records)")
        }
        assert "no_prompt_explanation" not in columns
        for table, rows in before.items():
            assert connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() == rows
    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        for table, rows in before.items():
            assert connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() == rows


def test_clean_database_upgrade_downgrade_reupgrade_cycle(tmp_path: Path) -> None:
    database_path = tmp_path / "clean.db"
    config = migration_config(database_path, tmp_path / "files")

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        assert "no_prompt_explanation" in {
            row[1] for row in connection.execute("PRAGMA table_info(framework_records)")
        }

    command.downgrade(config, "0002")
    with sqlite3.connect(database_path) as connection:
        assert "no_prompt_explanation" not in {
            row[1] for row in connection.execute("PRAGMA table_info(framework_records)")
        }

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        assert "no_prompt_explanation" in {
            row[1] for row in connection.execute("PRAGMA table_info(framework_records)")
        }
