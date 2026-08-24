import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from api.main import create_app


def create_workspace(client: TestClient) -> tuple[str, str]:
    client_id = client.post("/api/clients", json={"name": "Northwind Health"}).json()["id"]
    project = client.post(
        f"/api/clients/{client_id}/projects",
        json={"name": "HIPAA 2026"},
    ).json()
    assessment_id = client.get(f"/api/projects/{project['id']}/assessment").json()["id"]
    return project["id"], assessment_id


def record_path(project_id: str, assessment_id: str, record_id: str) -> str:
    return f"/api/projects/{project_id}/assessments/{assessment_id}/records/{record_id}"


def mapping_path(project_id: str, assessment_id: str) -> str:
    return f"/api/projects/{project_id}/assessments/{assessment_id}/evidence-mappings"


def audit_path(project_id: str, assessment_id: str) -> str:
    return f"/api/projects/{project_id}/assessments/{assessment_id}/audit"


def migration_config(database_path: Path, storage_path: Path | None = None) -> Config:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    if storage_path is not None:
        config.set_main_option("raintech.managed_storage_root", str(storage_path))
    return config


def test_client_project_and_hipaa_assessment_are_created_and_retrievable(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")

    with TestClient(app) as client:
        created_client = client.post(
            "/api/clients",
            json={"name": "Northwind Health"},
        )
        assert created_client.status_code == 201
        client_id = created_client.json()["id"]

        created_project = client.post(
            f"/api/clients/{client_id}/projects",
            json={"name": "HIPAA 2026"},
        )
        assert created_project.status_code == 201
        project = created_project.json()
        assert project["framework_version_id"] == "hipaa-45cfr164-2026-07-01"

        assessment = client.get(f"/api/projects/{project['id']}/assessment")
        assert assessment.status_code == 200
        payload = assessment.json()
        assert payload["framework"]["record_count"] == 194
        assert payload["framework"]["prompt_count"] == 1163
        assert payload["framework"]["determination_record_count"] == 149
        assert len(payload["work_list"]) == 149


def test_record_contract_preserves_parent_context_and_prompt_presentation_roles(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        detail = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(ii)(A)"))

        assert detail.status_code == 200
        payload = detail.json()
        assert payload["record"]["citation"] == "45 CFR 164.308(a)(1)(ii)(A)"
        assert payload["record"]["title"] == "Risk analysis"
        assert "accurate and thorough assessment" in payload["record"]["regulation_text"]
        assert payload["record"]["editable_determination"] is True
        assert payload["parent"]["record_id"] == "164.308(a)(1)(i)"
        assert payload["parent"]["editable_determination"] is False
        assert payload["parent"]["prompts_collapsed_by_default"] is True
        assert payload["parent_prompts"]
        assert payload["position"]["total"] == 149
        assert payload["position"]["current"] >= 1
        assert payload["prompts"]
        assert all(
            prompt["render_checkbox"] == (prompt["role"] == "assessment_check")
            for prompt in payload["prompts"]
        )


def test_determination_rules_and_parent_rollup_are_enforced_at_the_api(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        endpoint = f"/api/assessments/{assessment_id}/determinations"

        assert (
            client.put(f"{endpoint}/164.308(a)(1)(ii)(A)", json={"status": "N/A"}).status_code
            == 422
        )
        assert (
            client.put(f"{endpoint}/164.308(a)(1)(ii)(A)", json={"status": "Met"}).status_code
            == 422
        )
        assert (
            client.put(f"{endpoint}/164.308(a)(3)(ii)(A)", json={"status": "Pending"}).status_code
            == 422
        )
        assert (
            client.put(
                f"{endpoint}/164.308(a)(3)(ii)(A)",
                json={
                    "status": "Pending",
                    "addressable_disposition": "equivalent_alternative",
                },
            ).status_code
            == 422
        )
        assert (
            client.put(f"{endpoint}/164.308(a)(1)(i)", json={"status": "Pending"}).status_code
            == 422
        )

        for record_id, status in (
            ("164.308(a)(1)(ii)(A)", "Pending"),
            ("164.308(a)(1)(ii)(B)", "Not Met"),
        ):
            response = client.put(f"{endpoint}/{record_id}", json={"status": status})
            assert response.status_code == 200

        parent = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(i)")).json()
        assert parent["determination"]["status"] == "Not Met"
        assert parent["determination"]["derived"] is True

        for record_id in (
            "164.308(a)(1)(ii)(A)",
            "164.308(a)(1)(ii)(B)",
            "164.308(a)(1)(ii)(C)",
            "164.308(a)(1)(ii)(D)",
        ):
            response = client.put(
                f"{endpoint}/{record_id}",
                json={
                    "status": "Met",
                    "interview_observation": "Observed with security lead.",
                },
            )
            assert response.status_code == 200

        parent = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(i)")).json()
        assert parent["determination"]["status"] == "Met"


def test_evidence_reuse_notes_audit_and_restart_persistence(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("risk-register.txt", b"sanitized evidence", "text/plain")},
        )
        assert artifact.status_code == 201
        artifact_id = artifact.json()["id"]

        for record_id, rationale in (
            ("164.308(a)(1)(ii)(A)", "Supports the risk analysis process."),
            ("164.308(a)(1)(ii)(B)", "Supports risk treatment decisions."),
        ):
            mapped = client.post(
                mapping_path(project_id, assessment_id),
                json={
                    "artifact_id": artifact_id,
                    "record_id": record_id,
                    "rationale": rationale,
                },
            )
            assert mapped.status_code == 201

        note = client.put(
            f"/api/assessments/{assessment_id}/records/164.308(a)(1)(i)/note",
            json={"note": "Scope confirmed with the security officer."},
        )
        assert note.status_code == 200
        met = client.put(
            f"/api/assessments/{assessment_id}/determinations/164.308(a)(1)(ii)(A)",
            json={"status": "Met"},
        )
        assert met.status_code == 200
        first_mapping = client.get(
            record_path(project_id, assessment_id, "164.308(a)(1)(ii)(A)")
        ).json()["evidence"][0]["mapping_id"]
        refused_unmap = client.delete(
            f"{mapping_path(project_id, assessment_id)}/{first_mapping}"
        )
        assert refused_unmap.status_code == 422

        detail = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(ii)(A)")).json()
        assert detail["evidence"][0]["shared_record_count"] == 2

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        parent = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(i)")).json()
        child = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(ii)(A)")).json()
        assert parent["note"] == "Scope confirmed with the security officer."
        assert child["determination"]["status"] == "Met"
        assert child["evidence"][0]["rationale"] == "Supports the risk analysis process."

        audit = client.get(audit_path(project_id, assessment_id)).json()
        assert all(event["actor"]["id"] == "johnathan" for event in audit)
        actions = {event["action"] for event in audit}
        assert {"record.note_saved", "evidence.mapped", "determination.saved"} <= actions


def test_project_scoped_immutable_evidence_version_mapping_state_and_audit_isolation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    stored_bytes = b"synthetic sanitized risk register"
    with TestClient(app) as client:
        project_a_id, assessment_a_id = create_workspace(client)
        project_b_id, assessment_b_id = create_workspace(client)
        created = client.post(
            f"/api/projects/{project_a_id}/evidence",
            files={"file": ("synthetic-risk-register.txt", stored_bytes, "text/plain")},
        )
        assert created.status_code == 201
        artifact = created.json()
        assert artifact["version"] == {
            "id": artifact["version"]["id"],
            "project_id": project_a_id,
            "version_number": 1,
            "sha256": sha256(stored_bytes).hexdigest(),
            "relative_path": artifact["relative_path"],
            "created_at": artifact["created_at"],
        }
        assert (storage_path / artifact["relative_path"]).read_bytes() == stored_bytes
        with (
            sqlite3.connect(database_path) as connection,
            pytest.raises(sqlite3.IntegrityError, match="immutable"),
        ):
            connection.execute(
                "UPDATE evidence_versions SET sha256 = 'modified' WHERE id = ?",
                (artifact["version"]["id"],),
            )
        with (
            sqlite3.connect(database_path) as connection,
            pytest.raises(sqlite3.IntegrityError, match="immutable"),
        ):
            connection.execute(
                "DELETE FROM evidence_versions WHERE id = ?",
                (artifact["version"]["id"],),
            )

        mapped = client.post(
            f"/api/projects/{project_a_id}/assessments/{assessment_a_id}/evidence-mappings",
            json={
                "artifact_id": artifact["id"],
                "record_id": "164.308(a)(1)(ii)(A)",
                "rationale": "Synthetic evidence supports the risk analysis.",
            },
        )
        assert mapped.status_code == 201
        assert mapped.json()["review_state"] == "Not reviewed"
        detail = client.get(
            f"/api/projects/{project_a_id}/assessments/{assessment_a_id}"
            "/records/164.308(a)(1)(ii)(A)"
        )
        assert detail.status_code == 200
        assert detail.json()["evidence"][0]["sha256"] == sha256(stored_bytes).hexdigest()
        assert detail.json()["evidence"][0]["version_number"] == 1
        assert detail.json()["evidence"][0]["review_state"] == "Not reviewed"

        assert client.get(f"/api/projects/{project_b_id}/evidence").json() == []
        assert (
            client.post(
                f"/api/projects/{project_b_id}/assessments/{assessment_b_id}/evidence-mappings",
                json={
                    "artifact_id": artifact["id"],
                    "record_id": "164.308(a)(1)(ii)(A)",
                    "rationale": "Must not expose Project A evidence.",
                },
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/projects/{project_b_id}/assessments/{assessment_a_id}"
                "/records/164.308(a)(1)(ii)(A)"
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/projects/{project_b_id}/assessments/{assessment_a_id}/audit"
            ).status_code
            == 404
        )

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        detail = client.get(
            f"/api/projects/{project_a_id}/assessments/{assessment_a_id}"
            "/records/164.308(a)(1)(ii)(A)"
        )
        assert detail.status_code == 200
        evidence = detail.json()["evidence"][0]
        assert evidence["sha256"] == sha256(stored_bytes).hexdigest()
        assert evidence["review_state"] == "Not reviewed"
        audit = client.get(
            f"/api/projects/{project_a_id}/assessments/{assessment_a_id}/audit"
        ).json()
        assert any(event["action"] == "evidence.mapped" for event in audit)


def test_0001_evidence_artifact_upgrade_backfills_stored_bytes_without_hiding_mapping(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    project_id = "synthetic-project"
    assessment_id = "synthetic-assessment"
    artifact_id = "synthetic-artifact"
    relative_path = f"{project_id}/synthetic-artifact.txt"
    stored_bytes = b"synthetic existing 0001 evidence"
    command.upgrade(migration_config(database_path), "0001")
    stored_file = storage_path / relative_path
    stored_file.parent.mkdir(parents=True)
    stored_file.write_bytes(stored_bytes)
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            f"""
            INSERT INTO clients(id, name, created_at)
            VALUES ('synthetic-client', 'Synthetic Client', '2026-08-24T00:00:00+00:00');
            INSERT INTO projects(id, client_id, name, framework_version_id, created_at)
            VALUES (
                '{project_id}', 'synthetic-client', 'Synthetic HIPAA',
                'hipaa-45cfr164-2026-07-01', '2026-08-24T00:00:00+00:00'
            );
            INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES (
                '{assessment_id}', '{project_id}', 'hipaa-45cfr164-2026-07-01',
                '2026-08-24T00:00:00+00:00'
            );
            INSERT INTO evidence_artifacts(id, project_id, name, relative_path, created_at)
            VALUES (
                '{artifact_id}', '{project_id}', 'synthetic-artifact.txt',
                '{relative_path}', '2026-08-24T00:00:00+00:00'
            );
            INSERT INTO evidence_mappings(
                id, artifact_id, assessment_id, record_id, rationale, created_at
            )
            VALUES (
                'synthetic-mapping', '{artifact_id}', '{assessment_id}',
                '164.308(a)(1)(ii)(A)', 'Synthetic existing mapping.',
                '2026-08-24T00:00:00+00:00'
            );
            """
        )

    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        listed = client.get(f"/api/projects/{project_id}/evidence")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == artifact_id
        assert listed.json()[0]["sha256"] == sha256(stored_bytes).hexdigest()
        assert listed.json()[0]["version_number"] == 1
        detail = client.get(record_path(project_id, assessment_id, "164.308(a)(1)(ii)(A)"))
        assert detail.status_code == 200
        assert detail.json()["evidence"] == [
            {
                "mapping_id": "synthetic-mapping",
                "artifact_id": artifact_id,
                "name": "synthetic-artifact.txt",
                "relative_path": relative_path,
                "rationale": "Synthetic existing mapping.",
                "review_state": "Not reviewed",
                "version_id": f"{artifact_id}:1",
                "version_number": 1,
                "sha256": sha256(stored_bytes).hexdigest(),
                "shared_record_count": 1,
            }
        ]
    with sqlite3.connect(database_path) as connection:
        versions = connection.execute(
            "SELECT artifact_id, project_id, version_number, relative_path, sha256 "
            "FROM evidence_versions"
        ).fetchall()
    assert versions == [
        (
            artifact_id,
            project_id,
            1,
            relative_path,
            sha256(stored_bytes).hexdigest(),
        )
    ]
    config = migration_config(database_path, storage_path)
    command.downgrade(config, "0001")
    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_number, sha256 FROM evidence_versions"
        ).fetchall() == [(1, sha256(stored_bytes).hexdigest())]


def test_0001_evidence_artifact_upgrade_refuses_missing_stored_bytes(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    command.upgrade(migration_config(database_path), "0001")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO evidence_artifacts(id, project_id, name, relative_path, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "missing-artifact",
                "synthetic-project",
                "missing-artifact.txt",
                "synthetic-project/missing-artifact.txt",
                "2026-08-24T00:00:00+00:00",
            ),
        )
    with pytest.raises(RuntimeError, match="stored file is missing"):
        command.upgrade(migration_config(database_path, storage_path), "head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'evidence_versions'"
        ).fetchone() is None


def test_prompt_answers_and_cross_record_placements_survive_framework_reseed(
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
        prompt = next(item for item in source["prompts"] if "contingency plan" in item["text"])
        context_prompt = next(item for item in source["prompts"] if item["id"] != prompt["id"])

        answer = client.put(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/answer",
            json={"answer": "The client maintains CP-001 and tests it annually."},
        )
        assert answer.status_code == 200
        moved = client.put(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/placement",
            json={
                "destination_record_id": destination_id,
                "rule_citation": "45 CFR 164.308(a)(7)",
                "reason": "The question tests the contingency-plan standard.",
            },
        )
        assert moved.status_code == 200
        contextualized = client.put(
            f"/api/assessments/{assessment_id}/prompts/{context_prompt['id']}/placement",
            json={
                "destination_record_id": None,
                "rule_citation": "",
                "reason": "No governing rule can be named for this general practice.",
            },
        )
        assert contextualized.status_code == 200
        rejected = client.post(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/rejections",
            json={
                "proposed_record_id": "164.308(a)(1)(ii)(C)",
                "reason": "This proposal matched on vocabulary, not the governing rule.",
            },
        )
        assert rejected.status_code == 201
        rejections = client.get(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/rejections"
        ).json()
        assert [item["proposed_record_id"] for item in rejections] == [
            "164.308(a)(1)(ii)(C)"
        ]

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        source = client.get(record_path(project_id, assessment_id, source_id)).json()
        destination = client.get(record_path(project_id, assessment_id, destination_id)).json()
        assert all(item["id"] != prompt["id"] for item in source["prompts"])
        placed = next(item for item in destination["prompts"] if item["id"] == prompt["id"])
        assert placed["answer"] == "The client maintains CP-001 and tests it annually."
        assert placed["moved_from"]["record_id"] == source_id
        assert placed["placement"]["rule_citation"] == "45 CFR 164.308(a)(7)"
        assert any(
            item["id"] == context_prompt["id"] for item in destination["context_prompts"]
        )


def test_final_routine_retry_save_persists_and_audits_prompt_answer(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        record_id = "164.308(a)(1)(i)"
        record = client.get(record_path(project_id, assessment_id, record_id)).json()
        prompt = record["prompts"][0]

        first = client.put(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/answer",
            json={"answer": "Earlier draft that did not become the final retry."},
        )
        assert first.status_code == 200
        retry = client.put(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/answer",
            json={"answer": "Final retained draft after retry."},
        )
        assert retry.status_code == 200

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        record = client.get(record_path(project_id, assessment_id, record_id)).json()
        saved_prompt = next(item for item in record["prompts"] if item["id"] == prompt["id"])
        assert saved_prompt["answer"] == "Final retained draft after retry."

        prompt_audits = [
            event
            for event in client.get(audit_path(project_id, assessment_id)).json()
            if event["action"] == "prompt.answer_saved"
        ]
        assert len(prompt_audits) == 2
        assert all(event["actor"]["id"] == "johnathan" for event in prompt_audits)
