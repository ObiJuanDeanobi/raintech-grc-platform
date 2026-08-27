import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest
from alembic import command
from fastapi.testclient import TestClient

from api.database import configure_connection, register_profile_revision_function
from api.main import create_app
from api.tests.test_workspace_api import create_workspace, migration_config


def create_project(client: TestClient, suffix: str, framework_version_id: str | None = None) -> str:
    client_id = client.post(
        "/api/clients", json={"name": f"Synthetic Client {suffix}"}
    ).json()["id"]
    payload = {"name": f"{suffix} Profile"}
    if framework_version_id:
        payload["framework_version_id"] = framework_version_id
    response = client.post(f"/api/clients/{client_id}/projects", json=payload)
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def value(
    section: str,
    key: str,
    label: str,
    content: str,
    *,
    source: str = "Synthetic discovery interview",
    reviewer: str = "Johnathan",
    reviewed_at: str = "2026-08-26T20:00:00+00:00",
) -> dict[str, str]:
    return {
        "section": section,
        "field_key": key,
        "label": label,
        "value": content,
        "source": source,
        "reviewer": reviewer,
        "last_reviewed_at": reviewed_at,
    }


def profile_payload(expected_revision: str = "1") -> dict[str, object]:
    environment_key = "environment-cloud"
    return {
        "expected_revision": expected_revision,
        "values": [
            value("project_metadata", "delivery_context", "Delivery context", "Synthetic program"),
        ],
        "items": [
            {
                "client_key": environment_key,
                "item_type": "environment",
                "environment_item_key": None,
                "values": [
                    value("environments", "name", "Name", "Synthetic cloud"),
                    value("environments", "environment_type", "Environment type", "cloud"),
                ],
            },
            {
                "client_key": "scope-workstation",
                "item_type": "scope_item",
                "environment_item_key": environment_key,
                "values": [
                    value("scope_items", "name", "Name", "Synthetic workstation"),
                    value("scope_items", "description", "Description", "Inventory metadata only"),
                ],
            },
            {
                "client_key": "process-intake",
                "item_type": "business_process",
                "environment_item_key": None,
                "values": [value("business_processes", "name", "Name", "Client intake")],
            },
            {
                "client_key": "location-hq",
                "item_type": "location",
                "environment_item_key": None,
                "values": [value("locations", "name", "Name", "Synthetic headquarters")],
            },
            {
                "client_key": "vendor-msp",
                "item_type": "external_service",
                "environment_item_key": None,
                "values": [value("external_services", "name", "Name", "Synthetic MSP")],
            },
            {
                "client_key": "person-owner",
                "item_type": "person_role",
                "environment_item_key": None,
                "values": [value("people_roles", "name", "Name", "Security Officer")],
            },
            {
                "client_key": "exclusion-lab",
                "item_type": "exclusion_constraint",
                "environment_item_key": None,
                "values": [
                    value(
                        "exclusions_constraints",
                        "name",
                        "Name",
                        "Training lab excluded",
                    )
                ],
            },
            {
                "client_key": "reference-boundary",
                "item_type": "reference",
                "environment_item_key": None,
                "values": [value("references", "name", "Name", "Synthetic boundary memo")],
            },
            {
                "client_key": "unknown-count",
                "item_type": "unknown_follow_up",
                "environment_item_key": None,
                "values": [
                    value("unknowns_follow_up", "name", "Unknown", "Final endpoint count"),
                    value("unknowns_follow_up", "owner", "Owner", "Security Officer"),
                    value("unknowns_follow_up", "target_date", "Target date", "2026-09-15"),
                    value("unknowns_follow_up", "follow_up_reference", "Follow-up reference", ""),
                ],
            },
        ],
    }


def lifecycle_payload(
    client: TestClient,
    project_id: str,
    version_id: str,
    status: str,
    reviewer: str = "Johnathan",
) -> dict[str, str]:
    revision = client.get(
        f"/api/projects/{project_id}/profile/versions/{version_id}"
    ).json()["content_revision"]
    return {
        "status": status,
        "reviewer": reviewer,
        "expected_revision": revision,
    }


def current_revision(client: TestClient, project_id: str, version_id: str) -> str:
    return cast(
        str,
        client.get(
            f"/api/projects/{project_id}/profile/versions/{version_id}"
        ).json()["content_revision"],
    )


def direct_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    configure_connection(connection)
    return connection


def test_generic_profile_versions_lifecycle_provenance_and_immutability(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "HIPAA")
        initial = client.get(f"/api/projects/{project_id}/profile")
        assert initial.status_code == 200
        assert initial.json()["active_version_id"] is None
        draft = initial.json()["versions"][0]
        assert draft["version_number"] == 1
        assert draft["status"] == "Draft"
        assert initial.json()["template"] == {
            "available": False,
            "name": None,
            "message": (
                "No framework template is released. Use the complete neutral Profile form."
            ),
        }

        saved = client.put(
            f"/api/projects/{project_id}/profile/versions/{draft['id']}",
            json=profile_payload(draft["content_revision"]),
        )
        assert saved.status_code == 200
        payload = saved.json()
        assert {item["item_type"] for item in payload["items"]} == {
            "scope_item",
            "environment",
            "business_process",
            "location",
            "external_service",
            "person_role",
            "exclusion_constraint",
            "reference",
            "unknown_follow_up",
        }
        environment = next(item for item in payload["items"] if item["item_type"] == "environment")
        inventory = next(item for item in payload["items"] if item["item_type"] == "scope_item")
        assert inventory["environment_item_id"] == environment["id"]
        assert all(
            field["source"] and field["reviewer"] and field["last_reviewed_at"]
            for field in payload["values"]
            + [field for item in payload["items"] for field in item["values"]]
        )

        reviewed = client.post(
            f"/api/projects/{project_id}/profile/versions/{draft['id']}/lifecycle",
            json=lifecycle_payload(client, project_id, draft["id"], "Reviewed"),
        )
        assert reviewed.status_code == 201
        approved = client.post(
            f"/api/projects/{project_id}/profile/versions/{draft['id']}/lifecycle",
            json=lifecycle_payload(client, project_id, draft["id"], "Approved"),
        )
        assert approved.status_code == 201
        assert approved.json()["active_version_id"] == draft["id"]
        assert approved.json()["version"]["status"] == "Approved"
        assert [event["status"] for event in approved.json()["version"]["lifecycle"]] == [
            "Draft",
            "Reviewed",
            "Approved",
        ]
        assert all(
            event["actor"]["id"] == "johnathan"
            for event in approved.json()["version"]["lifecycle"]
        )
        assert approved.json()["version"]["lifecycle"][-1]["reviewer"] == "Johnathan"
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{draft['id']}",
            json=profile_payload(approved.json()["version"]["content_revision"]),
        ).status_code == 409

        version_2 = client.post(
            f"/api/projects/{project_id}/profile/versions",
            json={"base_version_id": draft["id"]},
        )
        assert version_2.status_code == 201
        assert version_2.json()["version_number"] == 2
        assert version_2.json()["status"] == "Draft"
        assert client.get(
            f"/api/projects/{project_id}/profile/versions/{draft['id']}"
        ).json()["status"] == "Approved"

    with direct_connection(database_path) as connection:
        version_id = connection.execute(
            "SELECT id FROM profile_versions WHERE project_id = ? ORDER BY version_number",
            (project_id,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE profile_field_values SET value = 'changed' WHERE profile_version_id = ?",
                (version_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE profile_lifecycle_events SET reviewer = 'changed' "
                "WHERE profile_version_id = ?",
                (version_id,),
            )


def test_unknown_validation_typed_evidence_reuse_upload_and_assessment_regression(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    stored_bytes = b"synthetic sanitized profile support"
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        profile = client.get(f"/api/projects/{project_id}/profile").json()
        version_id = profile["versions"][0]["id"]
        invalid = cast(dict[str, Any], profile_payload())
        unknown = next(
            item for item in invalid["items"] if item["item_type"] == "unknown_follow_up"
        )
        for field in unknown["values"]:
            if field["field_key"] in {"owner", "target_date", "follow_up_reference"}:
                field["value"] = ""
        response = client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}", json=invalid
        )
        assert response.status_code == 422
        assert (
            "owner and target date or an explicit follow-up reference"
            in response.json()["detail"]
        )
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json=profile_payload(profile["versions"][0]["content_revision"]),
        ).status_code == 200

        existing = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("existing.txt", b"existing sanitized bytes", "text/plain")},
        ).json()
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_id),
                "artifact_id": existing["id"],
                "evidence_version_id": existing["version"]["id"],
                "target_key": "field:does:not-exist",
                "rationale": "Invalid target.",
            },
        ).status_code == 404
        files_before_invalid_upload = sorted(storage_path.rglob("*"))
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence",
            data={
                "expected_revision": current_revision(client, project_id, version_id),
                "target_key": "item:missing:name",
                "rationale": "Invalid target.",
            },
            files={"file": ("invalid-target.txt", b"do not store", "text/plain")},
        ).status_code == 404
        assert sorted(storage_path.rglob("*")) == files_before_invalid_upload
        assessment_mapping = client.post(
            f"/api/projects/{project_id}/assessments/{assessment_id}/evidence-mappings",
            json={
                "artifact_id": existing["id"],
                "record_id": "164.308(a)(1)(ii)(A)",
                "rationale": "Assessment rationale remains assessment-owned.",
            },
        )
        assert assessment_mapping.status_code == 201
        mapped = client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_id),
                "artifact_id": existing["id"],
                "evidence_version_id": existing["version"]["id"],
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Supports the synthetic delivery context.",
            },
        )
        assert mapped.status_code == 201
        assert mapped.json()["target_type"] == "profile"
        assert mapped.json()["review_state"] == "Not reviewed"

        uploaded = client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence",
            data={
                "expected_revision": mapped.json()["content_revision"],
                "target_key": "item:reference-boundary:name",
                "rationale": "Supports the synthetic boundary reference.",
            },
            files={"file": ("profile-support.txt", stored_bytes, "text/plain")},
        )
        assert uploaded.status_code == 201
        uploaded_payload = uploaded.json()
        assert uploaded_payload["mapping"]["review_state"] == "Not reviewed"
        assert uploaded_payload["artifact"]["version"]["version_number"] == 1
        assert uploaded_payload["artifact"]["version"]["sha256"] == sha256(stored_bytes).hexdigest()
        assert (
            storage_path / uploaded_payload["artifact"]["relative_path"]
        ).read_bytes() == stored_bytes

        assessment_detail = client.get(
            f"/api/projects/{project_id}/assessments/{assessment_id}"
            "/records/164.308(a)(1)(ii)(A)"
        ).json()
        assert assessment_detail["evidence"][0]["rationale"] == (
            "Assessment rationale remains assessment-owned."
        )
        profile_detail = client.get(
            f"/api/projects/{project_id}/profile/versions/{version_id}"
        ).json()
        assert len(profile_detail["evidence"]) == 2
        assert {mapping["target_type"] for mapping in profile_detail["evidence"]} == {"profile"}


def test_profile_changed_seams_are_strictly_project_scoped_and_survive_restart(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        project_a = create_project(client, "A")
        project_b = create_project(client, "B")
        version_a = client.get(f"/api/projects/{project_a}/profile").json()["versions"][0]
        artifact_a = client.post(
            f"/api/projects/{project_a}/evidence",
            files={"file": ("a.txt", b"synthetic A", "text/plain")},
        ).json()
        before = client.get(f"/api/projects/{project_a}/profile/versions/{version_a['id']}").json()

        assert client.get(
            f"/api/projects/{project_b}/profile/versions/{version_a['id']}"
        ).status_code == 404
        assert client.put(
            f"/api/projects/{project_b}/profile/versions/{version_a['id']}",
            json=profile_payload(version_a["content_revision"]),
        ).status_code == 404
        assert client.post(
            f"/api/projects/{project_b}/profile/versions/{version_a['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": version_a["content_revision"],
            },
        ).status_code == 404
        assert client.post(
            f"/api/projects/{project_b}/profile/versions/{version_a['id']}/evidence-mappings",
            json={
                "expected_revision": version_a["content_revision"],
                "artifact_id": artifact_a["id"],
                "evidence_version_id": artifact_a["version"]["id"],
                "target_key": "project_metadata.context",
                "rationale": "Cross-project mutation must fail.",
            },
        ).status_code == 404
        after = client.get(f"/api/projects/{project_a}/profile/versions/{version_a['id']}").json()
        assert after == before

        assert client.put(
            f"/api/projects/{project_a}/profile/versions/{version_a['id']}",
            json=profile_payload(version_a["content_revision"]),
        ).status_code == 200
        assert client.post(
            f"/api/projects/{project_a}/profile/versions/{version_a['id']}/lifecycle",
            json=lifecycle_payload(client, project_a, version_a["id"], "Reviewed"),
        ).status_code == 201
        assert client.post(
            f"/api/projects/{project_a}/profile/versions/{version_a['id']}/lifecycle",
            json=lifecycle_payload(client, project_a, version_a["id"], "Approved"),
        ).status_code == 201

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        profile = client.get(f"/api/projects/{project_a}/profile").json()
        assert profile["active_version_id"] == version_a["id"]
        assert profile["versions"][0]["status"] == "Approved"
        audit = client.get(f"/api/projects/{project_a}/profile/audit").json()
        actions = {event["action"] for event in audit}
        assert {
            "profile.version_saved",
            "profile.lifecycle_recorded",
            "profile.version_approved",
        } <= actions
        assert all(event["actor"]["id"] == "johnathan" for event in audit)
        assert client.get(f"/api/projects/{project_b}/profile").json()["active_version_id"] is None


def test_hipaa_and_cmmc_projects_use_the_same_profile_contract(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        with direct_connection(database_path) as connection:
            hipaa = connection.execute(
                "SELECT declarations_json FROM framework_versions "
                "WHERE id = 'hipaa-45cfr164-2026-07-01'"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO framework_versions(
                    id, name, record_count, prompt_count, declarations_json
                ) VALUES ('cmmc-l2-synthetic', 'Synthetic CMMC Level 2', 0, 0, ?)
                """,
                (hipaa,),
            )
        hipaa_project = create_project(client, "HIPAA shared")
        cmmc_project = create_project(client, "CMMC shared", "cmmc-l2-synthetic")
        for project_id in (hipaa_project, cmmc_project):
            overview = client.get(f"/api/projects/{project_id}/profile")
            assert overview.status_code == 200
            assert overview.json()["template"]["available"] is False
            version_id = overview.json()["versions"][0]["id"]
            saved = client.put(
                f"/api/projects/{project_id}/profile/versions/{version_id}",
                json=profile_payload(overview.json()["versions"][0]["content_revision"]),
            )
            assert saved.status_code == 200
            assert saved.json()["items"][0]["item_type"] == "environment"


def test_populated_0004_upgrade_downgrade_reupgrade_preserves_existing_workspace(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    config = migration_config(database_path, storage_path)
    command.upgrade(config, "0004")
    timestamp = datetime.now(UTC).isoformat()
    relative_path = "project-existing/existing.txt"
    stored = storage_path / relative_path
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"synthetic existing evidence")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            f"""
            INSERT INTO user_accounts(id, display_name) VALUES ('johnathan', 'Johnathan');
            INSERT INTO framework_versions(
                id, name, record_count, prompt_count, declarations_json
            ) VALUES ('framework-existing', 'Synthetic', 0, 0, '{{}}');
            INSERT INTO clients(id, name, created_at)
            VALUES ('client-existing', 'Existing', '{timestamp}');
            INSERT INTO projects(id, client_id, name, framework_version_id, created_at)
            VALUES (
                'project-existing', 'client-existing', 'Existing Project',
                'framework-existing', '{timestamp}'
            );
            INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES ('assessment-existing', 'project-existing', 'framework-existing', '{timestamp}');
            INSERT INTO evidence_artifacts(id, project_id, name, relative_path, created_at)
            VALUES (
                'artifact-existing', 'project-existing', 'existing.txt',
                '{relative_path}', '{timestamp}'
            );
            INSERT INTO evidence_versions(
                id, artifact_id, project_id, version_number, relative_path, sha256, created_at
            ) VALUES (
                'version-existing', 'artifact-existing', 'project-existing', 1,
                '{relative_path}', '{sha256(stored.read_bytes()).hexdigest()}', '{timestamp}'
            );
            INSERT INTO evidence_mappings(
                id, artifact_id, assessment_id, record_id, rationale, review_state, created_at
            ) VALUES (
                'mapping-existing', 'artifact-existing', 'assessment-existing',
                'record-existing', 'Existing rationale', 'Not reviewed', '{timestamp}'
            );
            INSERT INTO prompt_answers(assessment_id, prompt_id, answer, updated_at)
            VALUES ('assessment-existing', 'prompt-existing', 'Existing answer', '{timestamp}');
            INSERT INTO prompt_move_rejections(
                assessment_id, prompt_id, proposed_record_id, reason, actor_id, created_at
            ) VALUES (
                'assessment-existing', 'prompt-existing', 'record-existing',
                'Existing rejection', 'johnathan', '{timestamp}'
            );
            INSERT INTO audit_events(
                id, actor_id, action, entity_type, entity_id, details_json, created_at
            ) VALUES (
                'audit-existing', 'johnathan', 'existing.action', 'assessment',
                'assessment-existing', '{{}}', '{timestamp}'
            );
            """
        )

    command.upgrade(config, "head")
    with direct_connection(database_path) as connection:
        assert connection.execute(
            "SELECT target_type, assessment_id, record_id, evidence_version_id "
            "FROM evidence_mappings WHERE id = 'mapping-existing'"
        ).fetchone() == (
            "assessment_record",
            "assessment-existing",
            "record-existing",
            "version-existing",
        )
        assert connection.execute(
            "SELECT version_number FROM profile_versions WHERE project_id = 'project-existing'"
        ).fetchone() == (1,)
    command.downgrade(config, "0004")
    with direct_connection(database_path) as connection:
        assert connection.execute(
            "SELECT artifact_id, assessment_id, record_id, rationale "
            "FROM evidence_mappings WHERE id = 'mapping-existing'"
        ).fetchone() == (
            "artifact-existing",
            "assessment-existing",
            "record-existing",
            "Existing rationale",
        )
        assert connection.execute(
            "SELECT answer FROM prompt_answers WHERE assessment_id = 'assessment-existing'"
        ).fetchone() == ("Existing answer",)
        assert connection.execute(
            "SELECT reason FROM prompt_move_rejections WHERE assessment_id = 'assessment-existing'"
        ).fetchone() == ("Existing rejection",)
        assert connection.execute(
            "SELECT action FROM audit_events WHERE id = 'audit-existing'"
        ).fetchone() == ("existing.action",)
    command.upgrade(config, "head")
    with direct_connection(database_path) as connection:
        assert connection.execute(
            "SELECT target_type FROM evidence_mappings WHERE id = 'mapping-existing'"
        ).fetchone() == ("assessment_record",)


def test_profile_mapping_destination_row_authorization_and_immutability(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_a = create_project(client, "Mapping A")
        project_b = create_project(client, "Mapping B")
        version_a = client.get(f"/api/projects/{project_a}/profile").json()["versions"][0]["id"]
        version_b = client.get(f"/api/projects/{project_b}/profile").json()["versions"][0]["id"]
        assert client.put(
            f"/api/projects/{project_a}/profile/versions/{version_a}",
            json=profile_payload(current_revision(client, project_a, version_a)),
        ).status_code == 200
        artifact = client.post(
            f"/api/projects/{project_a}/evidence",
            files={"file": ("mapping.txt", b"synthetic mapping", "text/plain")},
        ).json()
        mapping = client.post(
            f"/api/projects/{project_a}/profile/versions/{version_a}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_a, version_a),
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Original rationale.",
            },
        ).json()
        mapping_id = mapping["mapping_id"]
        before = client.get(
            f"/api/projects/{project_a}/profile/versions/{version_a}"
        ).json()["evidence"]
        assert client.put(
            f"/api/projects/{project_a}/profile/versions/{version_a}"
            f"/evidence-mappings/{mapping_id}",
            json={
                "actor_id": "missing-user",
                "expected_revision": current_revision(client, project_a, version_a),
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Unknown actor.",
            },
        ).status_code == 422
        assert client.delete(
            f"/api/projects/{project_a}/profile/versions/{version_a}"
            f"/evidence-mappings/{mapping_id}?actor_id=missing-user"
            f"&expected_revision={mapping['content_revision']}"
        ).status_code == 422

        assert client.delete(
            f"/api/projects/{project_b}/profile/versions/{version_b}"
            f"/evidence-mappings/{mapping_id}"
            f"?expected_revision={current_revision(client, project_b, version_b)}"
        ).status_code == 404
        assert client.delete(
            f"/api/projects/{project_a}/profile/versions/missing-version"
            f"/evidence-mappings/{mapping_id}?expected_revision=missing"
        ).status_code == 404
        assert client.put(
            f"/api/projects/{project_b}/profile/versions/{version_b}"
            f"/evidence-mappings/{mapping_id}",
            json={
                "expected_revision": current_revision(client, project_b, version_b),
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Cross-project overwrite.",
            },
        ).status_code == 404
        assert client.get(
            f"/api/projects/{project_a}/profile/versions/{version_a}"
        ).json()["evidence"] == before

        assert client.post(
            f"/api/projects/{project_a}/profile/versions/{version_a}/lifecycle",
            json=lifecycle_payload(client, project_a, version_a, "Reviewed"),
        ).status_code == 201
        assert client.delete(
            f"/api/projects/{project_a}/profile/versions/{version_a}"
            f"/evidence-mappings/{mapping_id}"
            f"?expected_revision={current_revision(client, project_a, version_a)}"
        ).status_code == 409
        assert client.post(
            f"/api/projects/{project_a}/profile/versions/{version_a}/lifecycle",
            json=lifecycle_payload(client, project_a, version_a, "Approved"),
        ).status_code == 201
        assert client.put(
            f"/api/projects/{project_a}/profile/versions/{version_a}"
            f"/evidence-mappings/{mapping_id}",
            json={
                "expected_revision": current_revision(client, project_a, version_a),
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Approved overwrite.",
            },
        ).status_code == 409


def test_profile_actor_validation_precedes_rows_files_and_audits(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        project_id = create_project(client, "Actor")
        profile = client.get(f"/api/projects/{project_id}/profile").json()
        version_id = profile["versions"][0]["id"]
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json={**profile_payload(), "actor_id": "missing-user"},
        ).status_code == 422
        assert client.post(
            f"/api/projects/{project_id}/profile/versions",
            json={"base_version_id": version_id, "actor_id": "missing-user"},
        ).status_code == 422
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "actor_id": "missing-user",
                "expected_revision": "1",
            },
        ).status_code == 422
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("actor.txt", b"actor test", "text/plain")},
        ).json()
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
            json={
                "actor_id": "missing-user",
                "expected_revision": current_revision(client, project_id, version_id),
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "field:project_metadata:project_name",
                "rationale": "Must not persist.",
            },
        ).status_code == 422
        before_files = sorted(path.relative_to(storage_path) for path in storage_path.rglob("*"))
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence",
            data={
                "actor_id": "missing-user",
                "expected_revision": current_revision(client, project_id, version_id),
                "target_key": "field:project_metadata:project_name",
                "rationale": "Must not persist.",
            },
            files={"file": ("actor-upload.txt", b"must not store", "text/plain")},
        ).status_code == 422
        assert (
            sorted(path.relative_to(storage_path) for path in storage_path.rglob("*"))
            == before_files
        )
        with direct_connection(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM profile_versions WHERE project_id = ?", (project_id,)
            ).fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM evidence_mappings WHERE profile_version_id = ?",
                (version_id,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT COUNT(*) FROM audit_events "
                "WHERE json_extract(details_json, '$.project_id') = ? "
                "AND action LIKE 'profile.%'",
                (project_id,),
            ).fetchone()[0] == 0


def test_same_name_profile_uploads_get_distinct_server_ids_and_mappings(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Same name")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        responses = []
        for target, content in (
            ("field:project_metadata:project_name", b"first"),
            ("field:project_metadata:project_name", b"second"),
        ):
            response = client.post(
                f"/api/projects/{project_id}/profile/versions/{version_id}/evidence",
                data={
                    "expected_revision": current_revision(client, project_id, version_id),
                    "target_key": target,
                    "rationale": f"Supports {content.decode()}.",
                },
                files={"file": ("same-name.txt", content, "text/plain")},
            )
            assert response.status_code == 201
            responses.append(response.json())
        assert responses[0]["artifact"]["name"] == responses[1]["artifact"]["name"]
        assert responses[0]["artifact"]["uploaded_file_id"] != responses[1]["artifact"][
            "uploaded_file_id"
        ]
        assert responses[0]["artifact"]["id"] != responses[1]["artifact"]["id"]
        assert responses[0]["mapping"]["mapping_id"] != responses[1]["mapping"]["mapping_id"]
        assert responses[0]["artifact"]["relative_path"] != responses[1]["artifact"][
            "relative_path"
        ]
        audit = client.get(f"/api/projects/{project_id}/profile/audit").json()
        uploaded_ids = {
            event["details"]["uploaded_file_id"]
            for event in audit
            if event["action"] == "evidence.created"
        }
        assert uploaded_ids == {
            responses[0]["artifact"]["uploaded_file_id"],
            responses[1]["artifact"]["uploaded_file_id"],
        }


def test_successor_clones_independent_profile_mappings_to_same_evidence_version(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Clone")
        version_1 = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("clone.txt", b"clone", "text/plain")},
        ).json()
        original = client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_1),
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "field:project_metadata:project_name",
                "rationale": "Clone this rationale.",
            },
        ).json()
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/lifecycle",
            json=lifecycle_payload(client, project_id, version_1, "Reviewed"),
        ).status_code == 201
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/lifecycle",
            json=lifecycle_payload(client, project_id, version_1, "Approved"),
        ).status_code == 201
        successor = client.post(
            f"/api/projects/{project_id}/profile/versions",
            json={"base_version_id": version_1},
        ).json()
        assert len(successor["evidence"]) == 1
        cloned = successor["evidence"][0]
        assert cloned["mapping_id"] != original["mapping_id"]
        assert cloned["evidence_version_id"] == original["evidence_version_id"]
        assert cloned["sha256"] == original["sha256"]
        assert cloned["target_key"] == original["target_key"]
        assert cloned["rationale"] == original["rationale"]


def test_inventory_requires_same_version_environment_and_no_other_item_can_reference_one(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Inventory")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        missing = cast(dict[str, Any], profile_payload())
        next(item for item in missing["items"] if item["item_type"] == "scope_item")[
            "environment_item_key"
        ] = None
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}", json=missing
        ).status_code == 422
        wrong_type = cast(dict[str, Any], profile_payload())
        next(item for item in wrong_type["items"] if item["item_type"] == "location")[
            "environment_item_key"
        ] = "environment-cloud"
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}", json=wrong_type
        ).status_code == 422


def test_direct_sql_profile_guards_fail_closed_and_keep_active_ledger_consistent(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_a = create_project(client, "SQL A")
        project_b = create_project(client, "SQL B")
        version_a = client.get(f"/api/projects/{project_a}/profile").json()["versions"][0]["id"]
        version_b = client.get(f"/api/projects/{project_b}/profile").json()["versions"][0]["id"]
        assert client.post(
            f"/api/projects/{project_a}/profile/versions/{version_a}/lifecycle",
            json=lifecycle_payload(client, project_a, version_a, "Reviewed"),
        ).status_code == 201
        reviewed_revision = current_revision(client, project_a, version_a)
        artifact_b = client.post(
            f"/api/projects/{project_b}/evidence",
            files={"file": ("b.txt", b"B", "text/plain")},
        ).json()
    with direct_connection(database_path) as connection:
        configure_connection(connection)
        field_b = connection.execute(
            "SELECT id FROM profile_field_values WHERE profile_version_id = ?", (version_b,)
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE profile_field_values SET profile_version_id = ? WHERE id = ?",
                (version_a, field_b),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO evidence_mappings(
                    id, project_id, artifact_id, evidence_version_id, target_type, assessment_id,
                    record_id, profile_version_id, target_key, rationale, review_state, created_at
                ) VALUES (
                    'cross-project', ?, ?, ?, 'profile', NULL, NULL, ?,
                    'field:project_metadata:project_name', 'cross', 'Not reviewed', ?
                )
                """,
                (
                    project_a,
                    artifact_b["id"],
                    artifact_b["version"]["id"],
                    version_a,
                    datetime.now(UTC).isoformat(),
                ),
            )
        lifecycle_id = connection.execute(
            "SELECT id FROM profile_lifecycle_events WHERE profile_version_id = ? LIMIT 1",
            (version_a,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE profile_lifecycle_events SET reviewer = 'changed' WHERE id = ?",
                (lifecycle_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM profile_lifecycle_events WHERE id = ?", (lifecycle_id,)
            )
        connection.execute(
            """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer,
                    content_revision, created_at
                ) VALUES (
                    'direct-approval', ?, 'Approved', 'johnathan', 'Johnathan', ?, ?
                )
                """,
                (
                    version_a,
                    reviewed_revision,
                    datetime.now(UTC).isoformat(),
                ),
        )
        assert connection.execute(
            "SELECT active_profile_version_id FROM projects WHERE id = ?", (project_a,)
        ).fetchone()[0] == version_a


def test_direct_sql_retarget_and_identity_bypasses_are_blocked(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Retarget")
        version_1 = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        artifact_1 = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("one.txt", b"one", "text/plain")},
        ).json()
        artifact_2 = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("two.txt", b"two", "text/plain")},
        ).json()
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/lifecycle",
            json=lifecycle_payload(client, project_id, version_1, "Reviewed"),
        ).status_code == 201
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/lifecycle",
            json=lifecycle_payload(client, project_id, version_1, "Approved"),
        ).status_code == 201
        version_2 = client.post(
            f"/api/projects/{project_id}/profile/versions",
            json={"base_version_id": version_1},
        ).json()["id"]
        mapping = client.post(
            f"/api/projects/{project_id}/profile/versions/{version_2}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_2),
                "artifact_id": artifact_1["id"],
                "evidence_version_id": artifact_1["version"]["id"],
                "target_key": "field:project_metadata:project_name",
                "rationale": "Draft mapping.",
            },
        ).json()
    with direct_connection(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        mapped_field = connection.execute(
            """
            SELECT id FROM profile_field_values
            WHERE profile_version_id = ? AND profile_item_id IS NULL
              AND section = 'project_metadata' AND field_key = 'project_name'
            """,
            (version_2,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM profile_field_values WHERE id = ?", (mapped_field,)
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE evidence_mappings SET profile_version_id = ? WHERE id = ?",
                (version_1, mapping["mapping_id"]),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO evidence_mappings(
                    id, project_id, artifact_id, evidence_version_id, target_type,
                    assessment_id, record_id, profile_version_id, target_key,
                    rationale, review_state, created_at
                ) VALUES (
                    'mismatched-version', ?, ?, ?, 'profile', NULL, NULL, ?,
                    'field:project_metadata:project_name', 'bad', 'Not reviewed', ?
                )
                """,
                (
                    project_id,
                    artifact_1["id"],
                    artifact_2["version"]["id"],
                    version_2,
                    datetime.now(UTC).isoformat(),
                ),
            )
        connection.execute(
            """
                INSERT INTO profile_versions(
                    id, project_id, version_number, created_by, created_at, content_revision
                ) VALUES ('no-ledger', ?, 99, 'johnathan', ?, '1')
            """,
            (project_id, datetime.now(UTC).isoformat()),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_items(
                    id, profile_version_id, client_key, item_type, environment_item_id, sort_order
                ) VALUES ('no-ledger-item', 'no-ledger', 'x', 'environment', NULL, 0)
                """
            )


@pytest.mark.parametrize(
    ("trigger_table", "method", "path_suffix", "payload"),
    [
        (
            "profile_field_values",
            "PUT",
            "",
            profile_payload(),
        ),
        (
            "profile_lifecycle_events",
            "POST",
            "/lifecycle",
            {
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": "1",
            },
        ),
        (
            "profile_versions",
            "POST",
            "/successor",
            {"base": True},
        ),
    ],
)
def test_trigger_integrity_errors_return_controlled_conflicts(
    tmp_path: Path,
    trigger_table: str,
    method: str,
    path_suffix: str,
    payload: dict[str, object],
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app, raise_server_exceptions=False) as client:
        project_id = create_project(client, trigger_table)
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        with direct_connection(database_path) as connection:
            operation = "DELETE" if trigger_table == "profile_field_values" else "INSERT"
            connection.execute(
                f"""
                CREATE TRIGGER force_{trigger_table}_failure
                BEFORE {operation} ON {trigger_table}
                BEGIN
                    SELECT RAISE(ABORT, 'forced profile integrity failure');
                END
                """
            )
        if path_suffix == "/successor":
            response = client.post(
                f"/api/projects/{project_id}/profile/versions",
                json={"base_version_id": version_id},
            )
        elif method == "PUT":
            payload = {
                **payload,
                "expected_revision": current_revision(client, project_id, version_id),
            }
            response = client.put(
                f"/api/projects/{project_id}/profile/versions/{version_id}",
                json=payload,
            )
        else:
            payload = {
                **payload,
                "expected_revision": current_revision(client, project_id, version_id),
            }
            response = client.post(
                f"/api/projects/{project_id}/profile/versions/{version_id}{path_suffix}",
                json=payload,
            )
        assert response.status_code == 409
        assert response.json()["detail"] == (
            "The requested mutation violates a persisted integrity rule."
        )


def test_mapping_trigger_integrity_error_returns_controlled_conflict(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app, raise_server_exceptions=False) as client:
        project_id = create_project(client, "Mapping trigger")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("trigger.txt", b"trigger", "text/plain")},
        ).json()
        with direct_connection(database_path) as connection:
            connection.execute(
                """
                CREATE TRIGGER force_profile_mapping_failure
                BEFORE INSERT ON evidence_mappings
                BEGIN
                    SELECT RAISE(ABORT, 'forced mapping integrity failure');
                END
                """
            )
        response = client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_id),
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "field:project_metadata:project_name",
                "rationale": "Must return a controlled conflict.",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"] == (
            "The requested mutation violates a persisted integrity rule."
        )


def test_active_pointer_cannot_be_cleared_or_rewound_behind_latest_approval(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Pointer")
        version_1 = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/lifecycle",
            json=lifecycle_payload(client, project_id, version_1, "Reviewed"),
        ).status_code == 201
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_1}/lifecycle",
            json=lifecycle_payload(client, project_id, version_1, "Approved"),
        ).status_code == 201
        version_2 = client.post(
            f"/api/projects/{project_id}/profile/versions",
            json={"base_version_id": version_1},
        ).json()["id"]
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_2}/lifecycle",
            json=lifecycle_payload(client, project_id, version_2, "Reviewed"),
        ).status_code == 201
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_2}/lifecycle",
            json=lifecycle_payload(client, project_id, version_2, "Approved"),
        ).status_code == 201
    with direct_connection(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE projects SET active_profile_version_id = NULL WHERE id = ?",
                (project_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE projects SET active_profile_version_id = ? WHERE id = ?",
                (version_1, project_id),
            )
        assert connection.execute(
            "SELECT active_profile_version_id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()[0] == version_2


def test_draft_revision_rejects_last_writer_and_review_of_unseen_content(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as first, TestClient(app) as second:
        project_id = create_project(first, "Revision")
        loaded_first = first.get(f"/api/projects/{project_id}/profile").json()["versions"][0]
        loaded_second = second.get(
            f"/api/projects/{project_id}/profile/versions/{loaded_first['id']}"
        ).json()
        first_payload = cast(dict[str, Any], profile_payload())
        first_payload["expected_revision"] = loaded_first["content_revision"]
        saved = first.put(
            f"/api/projects/{project_id}/profile/versions/{loaded_first['id']}",
            json=first_payload,
        )
        assert saved.status_code == 200
        assert saved.json()["content_revision"] != loaded_first["content_revision"]
        stale_payload = cast(dict[str, Any], profile_payload())
        stale_payload["expected_revision"] = loaded_second["content_revision"]
        assert second.put(
            f"/api/projects/{project_id}/profile/versions/{loaded_first['id']}",
            json=stale_payload,
        ).status_code == 409
        stale_review = second.post(
            f"/api/projects/{project_id}/profile/versions/{loaded_first['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": loaded_second["content_revision"],
            },
        )
        assert stale_review.status_code == 409
        current = first.get(
            f"/api/projects/{project_id}/profile/versions/{loaded_first['id']}"
        ).json()
        assert current["status"] == "Draft"
        assert current["content_revision"] == saved.json()["content_revision"]
        assert first.post(
            f"/api/projects/{project_id}/profile/versions/{loaded_first['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": current["content_revision"],
            },
        ).status_code == 201


def test_canonical_target_collisions_are_rejected_by_api_and_database(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Targets")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        duplicate_top = {
            "expected_revision": "1",
            "values": [
                value("meta", "duplicate", "First", "one"),
                value("meta", "duplicate", "Second", "two"),
            ],
            "items": [],
        }
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json=duplicate_top,
        ).status_code == 422
        duplicate_item = cast(dict[str, Any], profile_payload())
        duplicate_item["items"][0]["values"].append(
            value("environments", "name", "Duplicate name", "two")
        )
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json=duplicate_item,
        ).status_code == 422
        delimiter = cast(dict[str, Any], profile_payload())
        delimiter["items"][0]["client_key"] = "environment:collision"
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json=delimiter,
        ).status_code == 422
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json=profile_payload(current_revision(client, project_id, version_id)),
        ).status_code == 200
    with direct_connection(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_field_values(
                    id, profile_version_id, profile_item_id, section, field_key, label,
                    value, source, reviewer, last_reviewed_at, sort_order
                ) SELECT 'duplicate-direct', profile_version_id, NULL, section, field_key,
                         'Duplicate', value, source, reviewer, last_reviewed_at, 99
                  FROM profile_field_values
                 WHERE profile_version_id = ? AND profile_item_id IS NULL LIMIT 1
                """,
                (version_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_items(
                    id, profile_version_id, client_key, item_type, environment_item_id, sort_order
                ) VALUES ('delimiter-direct', ?, 'a:b', 'environment', NULL, 99)
                """,
                (version_id,),
            )
        item_id = connection.execute(
            "SELECT id FROM profile_items WHERE profile_version_id = ? LIMIT 1",
            (version_id,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_field_values(
                    id, profile_version_id, profile_item_id, section, field_key, label,
                    value, source, reviewer, last_reviewed_at, sort_order
                ) SELECT 'duplicate-item-direct', profile_version_id, profile_item_id,
                         section, field_key, 'Duplicate', value, source, reviewer,
                         last_reviewed_at, 100
                  FROM profile_field_values
                 WHERE profile_item_id = ? LIMIT 1
                """,
                (item_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_field_values(
                    id, profile_version_id, profile_item_id, section, field_key, label,
                    value, source, reviewer, last_reviewed_at, sort_order
                ) VALUES (
                    'delimiter-field-direct', ?, NULL, 'meta:collision', 'name',
                    'Delimiter', 'value', 'source', 'reviewer',
                    '2026-08-26T20:00:00+00:00', 101
                )
                """,
                (version_id,),
            )


def test_referenced_destination_rows_cannot_be_changed_directly(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Destination")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        assert client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}",
            json=profile_payload(current_revision(client, project_id, version_id)),
        ).status_code == 200
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("target.txt", b"target", "text/plain")},
        ).json()
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_id),
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "item:environment-cloud:name",
                "rationale": "Protect item identity.",
            },
        ).status_code == 201
    with direct_connection(database_path) as connection:
        environment_id = connection.execute(
            "SELECT id FROM profile_items WHERE profile_version_id = ? AND item_type='environment'",
            (version_id,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE profile_items SET client_key='changed' WHERE id=?", (environment_id,)
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE profile_items SET item_type='location' WHERE id=?", (environment_id,)
            )
        other_version = connection.execute(
            """
            SELECT id FROM profile_versions
            WHERE project_id = (SELECT project_id FROM profile_versions WHERE id = ?)
              AND id != ?
            LIMIT 1
            """,
            (version_id, version_id),
        ).fetchone()
        if other_version is None:
            connection.execute(
                """
                INSERT INTO profile_versions(
                    id, project_id, version_number, created_by, created_at, content_revision
                )
                SELECT 'destination-other-version', project_id, 99, created_by, created_at, '1'
                FROM profile_versions WHERE id = ?
                """,
                (version_id,),
            )
            connection.execute(
                """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer, created_at
                ) VALUES (
                    'destination-other-draft', 'destination-other-version', 'Draft',
                    'johnathan', '', '2026-08-26T20:00:00+00:00'
                )
                """
            )
            other_version_id = "destination-other-version"
        else:
            other_version_id = other_version[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE profile_items SET profile_version_id=? WHERE id=?",
                (other_version_id, environment_id),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM profile_items WHERE id=?", (environment_id,))


def test_scope_first_successor_clone_preserves_sort_and_mappings(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Scope first")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        payload = cast(
            dict[str, Any],
            profile_payload(current_revision(client, project_id, version_id)),
        )
        scope = next(item for item in payload["items"] if item["item_type"] == "scope_item")
        environment = next(item for item in payload["items"] if item["item_type"] == "environment")
        payload["items"].remove(scope)
        payload["items"].remove(environment)
        payload["items"] = [scope, environment, *payload["items"]]
        saved = client.put(
            f"/api/projects/{project_id}/profile/versions/{version_id}", json=payload
        ).json()
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("scope.txt", b"scope", "text/plain")},
        ).json()
        client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
            json={
                "expected_revision": current_revision(client, project_id, version_id),
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "item:scope-workstation:name",
                "rationale": "Clone scope mapping.",
            },
        ).raise_for_status()
        client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/lifecycle",
            json=lifecycle_payload(client, project_id, version_id, "Reviewed"),
        ).raise_for_status()
        client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/lifecycle",
            json=lifecycle_payload(client, project_id, version_id, "Approved"),
        ).raise_for_status()
        successor = client.post(
            f"/api/projects/{project_id}/profile/versions",
            json={"base_version_id": version_id},
        )
        assert successor.status_code == 201
        assert [item["client_key"] for item in successor.json()["items"][:2]] == [
            "scope-workstation",
            "environment-cloud",
        ]
        assert len(successor.json()["evidence"]) == 1
        assert saved["items"][0]["sort_order"] == 0


def test_failed_profile_upload_leaves_no_rows_or_managed_bytes(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        project_id = create_project(client, "Upload cleanup")
        version_id = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]["id"]
        with direct_connection(database_path) as connection:
            connection.execute(
                """
                CREATE TRIGGER force_upload_mapping_failure
                BEFORE INSERT ON evidence_mappings
                WHEN NEW.target_type = 'profile'
                BEGIN
                    SELECT RAISE(ABORT, 'forced upload mapping failure');
                END
                """
            )
        before_files = sorted(path for path in storage_path.rglob("*") if path.is_file())
        response = client.post(
            f"/api/projects/{project_id}/profile/versions/{version_id}/evidence",
            data={
                "expected_revision": current_revision(client, project_id, version_id),
                "target_key": "field:project_metadata:project_name",
                "rationale": "Force cleanup.",
            },
            files={"file": ("orphan.txt", b"must be removed", "text/plain")},
        )
        assert response.status_code == 409
        assert sorted(path for path in storage_path.rglob("*") if path.is_file()) == before_files
        with direct_connection(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM evidence_artifacts WHERE project_id = ?", (project_id,)
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT COUNT(*) FROM evidence_mappings WHERE profile_version_id = ?",
                (version_id,),
            ).fetchone()[0] == 0


def test_every_profile_evidence_mutation_invalidates_stale_review_and_approval(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as first, TestClient(app) as second:
        project_id = create_project(first, "Whole snapshot revision")
        version = first.get(f"/api/projects/{project_id}/profile").json()["versions"][0]
        saved = first.put(
            f"/api/projects/{project_id}/profile/versions/{version['id']}",
            json=profile_payload(version["content_revision"]),
        ).json()
        artifact = first.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("revision.txt", b"revision evidence", "text/plain")},
        ).json()

        stale_before_reuse = saved["content_revision"]
        reused = first.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/evidence-mappings",
            json={
                "expected_revision": stale_before_reuse,
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Initial rationale.",
            },
        )
        assert reused.status_code == 201
        reuse_revision = reused.json()["content_revision"]
        assert reuse_revision != stale_before_reuse
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/evidence-mappings",
            json={
                "expected_revision": stale_before_reuse,
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "item:reference-boundary:name",
                "rationale": "Stale reuse.",
            },
        ).status_code == 409
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Second reviewer",
                "expected_revision": stale_before_reuse,
            },
        ).status_code == 409

        updated = first.put(
            f"/api/projects/{project_id}/profile/versions/{version['id']}"
            f"/evidence-mappings/{reused.json()['mapping_id']}",
            json={
                "expected_revision": reuse_revision,
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Updated rationale.",
            },
        )
        assert updated.status_code == 200
        update_revision = updated.json()["content_revision"]
        assert update_revision != reuse_revision
        assert second.put(
            f"/api/projects/{project_id}/profile/versions/{version['id']}"
            f"/evidence-mappings/{reused.json()['mapping_id']}",
            json={
                "expected_revision": reuse_revision,
                "target_key": "field:project_metadata:delivery_context",
                "rationale": "Stale update.",
            },
        ).status_code == 409
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Second reviewer",
                "expected_revision": reuse_revision,
            },
        ).status_code == 409

        uploaded = first.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/evidence",
            data={
                "expected_revision": update_revision,
                "target_key": "item:reference-boundary:name",
                "rationale": "Uploaded revision evidence.",
            },
            files={"file": ("uploaded.txt", b"uploaded revision", "text/plain")},
        )
        assert uploaded.status_code == 201
        upload_revision = uploaded.json()["content_revision"]
        assert upload_revision != update_revision
        stale_upload_files = sorted(
            path for path in (tmp_path / "files").rglob("*") if path.is_file()
        )
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/evidence",
            data={
                "expected_revision": update_revision,
                "target_key": "item:scope-workstation:name",
                "rationale": "Stale upload.",
            },
            files={"file": ("stale.txt", b"must not persist", "text/plain")},
        ).status_code == 409
        assert sorted(
            path for path in (tmp_path / "files").rglob("*") if path.is_file()
        ) == stale_upload_files
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Second reviewer",
                "expected_revision": update_revision,
            },
        ).status_code == 409

        deleted = first.delete(
            f"/api/projects/{project_id}/profile/versions/{version['id']}"
            f"/evidence-mappings/{reused.json()['mapping_id']}"
            f"?expected_revision={upload_revision}"
        )
        assert deleted.status_code == 200
        delete_revision = deleted.json()["content_revision"]
        assert delete_revision != upload_revision
        assert second.delete(
            f"/api/projects/{project_id}/profile/versions/{version['id']}"
            f"/evidence-mappings/{uploaded.json()['mapping']['mapping_id']}"
            f"?expected_revision={upload_revision}"
        ).status_code == 409
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Second reviewer",
                "expected_revision": upload_revision,
            },
        ).status_code == 409

        reviewed = first.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": delete_revision,
            },
        )
        assert reviewed.status_code == 201
        assert reviewed.json()["version"]["lifecycle"][-1]["content_revision"] == delete_revision
        assert second.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Approved",
                "reviewer": "Second reviewer",
                "expected_revision": upload_revision,
            },
        ).status_code == 409
        approved = first.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Approved",
                "reviewer": "Johnathan",
                "expected_revision": delete_revision,
            },
        )
        assert approved.status_code == 201
        assert approved.json()["version"]["lifecycle"][-1]["content_revision"] == delete_revision


def test_direct_sql_profile_content_change_invalidates_loaded_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Direct content revision")
        version = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]
        loaded_revision = version["content_revision"]
        with direct_connection(database_path) as connection:
            connection.execute(
                """
                UPDATE profile_field_values
                SET value = 'changed directly'
                WHERE profile_version_id = ? AND profile_item_id IS NULL
                """,
                (version["id"],),
            )
            with pytest.raises(sqlite3.DatabaseError):
                connection.execute(
                    """
                    INSERT INTO profile_content_changes(
                        profile_version_id, revision_token
                    ) VALUES (?, ?)
                    """,
                    (version["id"], loaded_revision),
                )
        changed_revision = current_revision(client, project_id, version["id"])
        assert changed_revision != loaded_revision
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": loaded_revision,
            },
        ).status_code == 409
        reviewed = client.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": changed_revision,
            },
        )
        assert reviewed.status_code == 201
        assert reviewed.json()["version"]["lifecycle"][-1]["content_revision"] == changed_revision


def test_active_pointer_is_unconditionally_null_before_approval(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_a = create_project(client, "Pointer preapproval A")
        project_b = create_project(client, "Pointer preapproval B")
        version_a = client.get(f"/api/projects/{project_a}/profile").json()["versions"][0]["id"]
        version_b = client.get(f"/api/projects/{project_b}/profile").json()["versions"][0]["id"]
    with direct_connection(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for target_project, invalid in (
            (project_a, "missing-version"),
            (project_a, version_a),
            (project_a, version_b),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE projects SET active_profile_version_id = ? WHERE id = ?",
                    (invalid, target_project),
                )
        client_id, framework_id = connection.execute(
            "SELECT client_id, framework_version_id FROM projects WHERE id = ?",
            (project_a,),
        ).fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO projects(
                    id, client_id, name, framework_version_id, created_at,
                    active_profile_version_id
                ) VALUES (
                    'invalid-pointer-project', ?, 'Invalid pointer', ?,
                    '2026-08-26T00:00:00+00:00', 'missing-version'
                )
                """,
                (client_id, framework_id),
            )


def test_database_rejects_bogus_and_stale_lifecycle_revisions(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Database lifecycle revision")
        version = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]
        loaded_revision = version["content_revision"]

    with direct_connection(database_path) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                """
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                VALUES (?, 'caller-forged-token')
                """,
                (version["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer,
                    content_revision, created_at
                ) VALUES (
                    'bogus-reviewed', ?, 'Reviewed', 'johnathan', 'Reviewer',
                    'not-the-current-hash', '2026-08-26T00:00:00+00:00'
                )
                """,
                (version["id"],),
            )
        connection.execute(
            """
            UPDATE profile_field_values SET value = 'directly changed'
            WHERE profile_version_id = ? AND profile_item_id IS NULL
            """,
            (version["id"],),
        )
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                """
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                VALUES (?, ?)
                """,
                (version["id"], loaded_revision),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE profile_versions
                SET content_revision = ?, revision_valid = 1
                WHERE id = ?
                """,
                (loaded_revision, version["id"]),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer,
                    content_revision, created_at
                ) VALUES (
                    'stale-reviewed', ?, 'Reviewed', 'johnathan', 'Reviewer',
                    ?, '2026-08-26T00:00:00+00:00'
                )
                """,
                (version["id"], loaded_revision),
            )

        current_revision_value = connection.execute(
            """
            SELECT revision_token FROM profile_content_changes
            WHERE profile_version_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (version["id"],),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO profile_lifecycle_events(
                id, profile_version_id, status, actor_id, reviewer,
                content_revision, created_at
            ) VALUES (
                'valid-reviewed', ?, 'Reviewed', 'johnathan', 'Reviewer',
                ?, '2026-08-26T00:00:01+00:00'
            )
            """,
            (version["id"], current_revision_value),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE profile_versions
                SET content_revision = 'forged-approved', revision_valid = 1
                WHERE id = ?
                """,
                (version["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer,
                    content_revision, created_at
                ) VALUES (
                    'bogus-approved', ?, 'Approved', 'johnathan', 'Reviewer',
                    'not-the-reviewed-hash', '2026-08-26T00:00:02+00:00'
                )
                """,
                (version["id"],),
            )
        connection.execute(
            """
            INSERT INTO profile_lifecycle_events(
                id, profile_version_id, status, actor_id, reviewer,
                content_revision, created_at
            ) VALUES (
                'valid-approved', ?, 'Approved', 'johnathan', 'Reviewer',
                ?, '2026-08-26T00:00:03+00:00'
            )
            """,
            (version["id"], current_revision_value),
        )


def test_approved_profile_uses_immutable_evidence_display_snapshot(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Immutable evidence display")
        version = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("original-name.txt", b"immutable bytes", "text/plain")},
        ).json()
        mapped = client.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/evidence-mappings",
            json={
                "expected_revision": version["content_revision"],
                "artifact_id": artifact["id"],
                "evidence_version_id": artifact["version"]["id"],
                "target_key": "field:project_metadata:project_name",
                "rationale": "Immutable display identity.",
            },
        ).json()
        assert client.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Reviewed",
                "reviewer": "Johnathan",
                "expected_revision": mapped["content_revision"],
            },
        ).status_code == 201
        approved = client.post(
            f"/api/projects/{project_id}/profile/versions/{version['id']}/lifecycle",
            json={
                "status": "Approved",
                "reviewer": "Johnathan",
                "expected_revision": mapped["content_revision"],
            },
        ).json()["version"]
        approved_mapping = approved["evidence"][0]
        approved_revision = approved["content_revision"]

    with direct_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE evidence_artifacts
            SET name = 'mutated-live-name.txt', uploaded_file_id = 'mutated-live-upload-id'
            WHERE id = ?
            """,
            (artifact["id"],),
        )

    with TestClient(app) as client:
        after = client.get(
            f"/api/projects/{project_id}/profile/versions/{version['id']}"
        ).json()
        assert after["content_revision"] == approved_revision
        assert after["lifecycle"][-1]["content_revision"] == approved_revision
        assert after["evidence"][0]["name"] == approved_mapping["name"]
        assert (
            after["evidence"][0]["uploaded_file_id"]
            == approved_mapping["uploaded_file_id"]
        )


def test_alembic_style_registered_connection_denies_direct_ledger_generation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    app = create_app(database_path=database_path, storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id = create_project(client, "Alembic authorizer")
        version = client.get(f"/api/projects/{project_id}/profile").json()["versions"][0]
    with sqlite3.connect(database_path) as connection:
        register_profile_revision_function(connection)
        before = connection.execute(
            "SELECT COUNT(*) FROM profile_content_changes WHERE profile_version_id = ?",
            (version["id"],),
        ).fetchone()[0]
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                """
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                SELECT ?, profile_snapshot_revision(?, ?)
                """,
                (version["id"], version["id"], before + 1),
            )
        assert connection.execute(
            "SELECT COUNT(*) FROM profile_content_changes WHERE profile_version_id = ?",
            (version["id"],),
        ).fetchone()[0] == before
