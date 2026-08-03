from pathlib import Path

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


def save_assessment_questions(
    client: TestClient,
    assessment_id: str,
    record_id: str,
    status: str,
) -> None:
    detail = client.get(f"/api/assessments/{assessment_id}/records/{record_id}").json()
    questions = [prompt for prompt in detail["prompts"] if prompt["role"] == "assessment_check"]
    assert questions
    for prompt in questions:
        payload = {"status": status}
        if status == "Met":
            payload["interview_observation"] = "Confirmed with the security lead."
        response = client.put(
            f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/working-record",
            json=payload,
        )
        assert response.status_code == 200


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
        _, assessment_id = create_workspace(client)
        detail = client.get(f"/api/assessments/{assessment_id}/records/164.308(a)(1)(ii)(A)")

        assert detail.status_code == 200
        payload = detail.json()
        assert payload["record"]["citation"] == "45 CFR 164.308(a)(1)(ii)(A)"
        assert payload["record"]["title"] == "Risk analysis"
        assert "accurate and thorough assessment" in payload["record"]["regulation_text"]
        assert payload["record"]["editable_determination"] is False
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
        assert all(
            (prompt["working_record"] is not None)
            == (prompt["role"] == "assessment_check")
            for prompt in payload["prompts"]
        )
        parent_detail = client.get(
            f"/api/assessments/{assessment_id}/records/164.308(a)(1)(i)"
        ).json()
        guidance = next(
            prompt for prompt in parent_detail["prompts"] if prompt["role"] == "context"
        )
        assert guidance["working_record"] is None


def test_determination_rules_and_parent_rollup_are_enforced_at_the_api(
    tmp_path: Path,
) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        _, assessment_id = create_workspace(client)
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

        save_assessment_questions(client, assessment_id, "164.308(a)(1)(ii)(A)", "Pending")
        save_assessment_questions(client, assessment_id, "164.308(a)(1)(ii)(B)", "Not Met")

        parent = client.get(f"/api/assessments/{assessment_id}/records/164.308(a)(1)(i)").json()
        assert parent["determination"]["status"] == "Not Met"
        assert parent["determination"]["derived"] is True

        for record_id in (
            "164.308(a)(1)(ii)(A)",
            "164.308(a)(1)(ii)(B)",
            "164.308(a)(1)(ii)(C)",
            "164.308(a)(1)(ii)(D)",
        ):
            save_assessment_questions(client, assessment_id, record_id, "Met")
        save_assessment_questions(client, assessment_id, "164.308(a)(1)(i)", "Met")

        parent = client.get(f"/api/assessments/{assessment_id}/records/164.308(a)(1)(i)").json()
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

        prompt_ids = []
        for record_id, rationale in (
            ("164.308(a)(1)(ii)(A)", "Supports the risk analysis process."),
            ("164.308(a)(1)(ii)(B)", "Supports risk treatment decisions."),
        ):
            record = client.get(
                f"/api/assessments/{assessment_id}/records/{record_id}"
            ).json()
            prompt_id = next(
                prompt["id"]
                for prompt in record["prompts"]
                if prompt["role"] == "assessment_check"
            )
            prompt_ids.append(prompt_id)
            mapped = client.post(
                f"/api/assessments/{assessment_id}/prompt-evidence-mappings",
                json={
                    "artifact_id": artifact_id,
                    "prompt_id": prompt_id,
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
            f"/api/assessments/{assessment_id}/prompts/{prompt_ids[0]}/working-record",
            json={"status": "Met"},
        )
        assert met.status_code == 200
        first_prompt = next(
            prompt
            for prompt in client.get(
                f"/api/assessments/{assessment_id}/records/164.308(a)(1)(ii)(A)"
            ).json()["prompts"]
            if prompt["id"] == prompt_ids[0]
        )
        first_mapping = first_prompt["working_record"]["evidence"][0]["mapping_id"]
        refused_unmap = client.delete(
            f"/api/assessments/{assessment_id}/prompt-evidence-mappings/{first_mapping}"
        )
        assert refused_unmap.status_code == 422

        detail = client.get(
            f"/api/assessments/{assessment_id}/records/164.308(a)(1)(ii)(A)"
        ).json()
        first_prompt = next(prompt for prompt in detail["prompts"] if prompt["id"] == prompt_ids[0])
        assert first_prompt["working_record"]["evidence"][0]["shared_record_count"] == 2

        for prompt in detail["prompts"]:
            if prompt["role"] == "assessment_check" and prompt["id"] != prompt_ids[0]:
                response = client.put(
                    f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/working-record",
                    json={
                        "status": "Met",
                        "interview_observation": "Confirmed with the security lead.",
                    },
                )
                assert response.status_code == 200

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        parent = client.get(f"/api/assessments/{assessment_id}/records/164.308(a)(1)(i)").json()
        child = client.get(f"/api/assessments/{assessment_id}/records/164.308(a)(1)(ii)(A)").json()
        assert parent["note"] == "Scope confirmed with the security officer."
        assert child["determination"]["status"] == "Met"
        first_prompt = next(prompt for prompt in child["prompts"] if prompt["id"] == prompt_ids[0])
        assert (
            first_prompt["working_record"]["evidence"][0]["rationale"]
            == "Supports the risk analysis process."
        )

        audit = client.get(f"/api/assessments/{assessment_id}/audit").json()
        assert all(event["actor"]["id"] == "johnathan" for event in audit)
        actions = {event["action"] for event in audit}
        assert {
            "record.note_saved",
            "evidence.mapped_to_prompt",
            "prompt.working_record_saved",
        } <= actions


def test_assessment_questions_have_persistent_working_records_and_drive_status(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)

    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        record_id = "164.308(a)(1)(ii)(A)"
        detail = client.get(
            f"/api/assessments/{assessment_id}/records/{record_id}"
        ).json()
        assessment_questions = [
            prompt for prompt in detail["prompts"] if prompt["role"] == "assessment_check"
        ]
        assert assessment_questions
        assert all(prompt["working_record"]["status"] == "" for prompt in assessment_questions)
        assert all(prompt["working_record"]["note"] == "" for prompt in assessment_questions)
        assert all(prompt["working_record"]["evidence"] == [] for prompt in assessment_questions)
        first = assessment_questions[0]
        working_endpoint = (
            f"/api/assessments/{assessment_id}/prompts/{first['id']}/working-record"
        )
        assert client.put(working_endpoint, json={"status": "N/A"}).status_code == 422
        assert client.put(working_endpoint, json={"status": "Met"}).status_code == 422

        pending = client.put(
            working_endpoint,
            json={
                "status": "Pending",
                "note": "Confirm the system inventory with the security lead.",
            },
        )
        assert pending.status_code == 200
        assert pending.json()["status"] == "Pending"
        assert pending.json()["note"] == "Confirm the system inventory with the security lead."

        detail = client.get(
            f"/api/assessments/{assessment_id}/records/{record_id}"
        ).json()
        assert detail["determination"]["status"] == "Pending"
        assert detail["determination"]["derived"] is True

        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("inventory.txt", b"sanitized inventory", "text/plain")},
        ).json()
        mapped = client.post(
            f"/api/assessments/{assessment_id}/prompt-evidence-mappings",
            json={
                "artifact_id": artifact["id"],
                "prompt_id": first["id"],
                "rationale": "",
            },
        )
        assert mapped.status_code == 201
        assert mapped.json()["rationale"] == ""

        assert (
            client.put(
                working_endpoint,
                json={
                    "status": "Met",
                    "note": "Confirm the system inventory with the security lead.",
                },
            ).status_code
            == 200
        )
        for prompt in assessment_questions[1:]:
            response = client.put(
                f"/api/assessments/{assessment_id}/prompts/{prompt['id']}/working-record",
                json={
                    "status": "Met",
                    "interview_observation": "Confirmed with the security lead.",
                },
            )
            assert response.status_code == 200

        detail = client.get(
            f"/api/assessments/{assessment_id}/records/{record_id}"
        ).json()
        assert detail["determination"]["status"] == "Met"
        assert detail["determination"]["derived"] is True
        first_reloaded = next(prompt for prompt in detail["prompts"] if prompt["id"] == first["id"])
        assert first_reloaded["working_record"]["evidence"][0]["rationale"] == ""

        assessment = client.get(f"/api/projects/{project_id}/assessment").json()
        work_item = next(item for item in assessment["work_list"] if item["record_id"] == record_id)
        assert work_item["determination"]["status"] == "Met"

    restarted = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(restarted) as client:
        detail = client.get(
            f"/api/assessments/{assessment_id}/records/{record_id}"
        ).json()
        first_reloaded = next(prompt for prompt in detail["prompts"] if prompt["id"] == first["id"])
        assert first_reloaded["working_record"]["status"] == "Met"
        assert (
            first_reloaded["working_record"]["note"]
            == "Confirm the system inventory with the security lead."
        )


def test_evidence_support_rationale_is_optional_for_record_mappings(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    with TestClient(app) as client:
        project_id, assessment_id = create_workspace(client)
        artifact = client.post(
            f"/api/projects/{project_id}/evidence",
            files={"file": ("policy.txt", b"sanitized policy", "text/plain")},
        ).json()

        mapped = client.post(
            f"/api/assessments/{assessment_id}/evidence-mappings",
            json={
                "artifact_id": artifact["id"],
                "record_id": "164.308(a)(1)(ii)(B)",
                "rationale": "",
            },
        )

        assert mapped.status_code == 201
        assert mapped.json()["rationale"] == ""


def test_prompt_answers_and_cross_record_placements_survive_framework_reseed(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    storage_path = tmp_path / "files"
    app = create_app(database_path=database_path, storage_path=storage_path)
    with TestClient(app) as client:
        _, assessment_id = create_workspace(client)
        source_id = "164.308(a)(1)(i)"
        destination_id = "164.308(a)(7)(i)"
        source = client.get(f"/api/assessments/{assessment_id}/records/{source_id}").json()
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
        source = client.get(f"/api/assessments/{assessment_id}/records/{source_id}").json()
        destination = client.get(
            f"/api/assessments/{assessment_id}/records/{destination_id}"
        ).json()
        assert all(item["id"] != prompt["id"] for item in source["prompts"])
        placed = next(item for item in destination["prompts"] if item["id"] == prompt["id"])
        assert placed["answer"] == "The client maintains CP-001 and tests it annually."
        assert placed["moved_from"]["record_id"] == source_id
        assert placed["placement"]["rule_citation"] == "45 CFR 164.308(a)(7)"
        assert any(
            item["id"] == context_prompt["id"] for item in destination["context_prompts"]
        )
