"""CMMC objective-level assessment and derived requirement rollup (Issue #104)."""

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

REQUIREMENT = "AC.L2-3.1.1"
OBJECTIVES = [f"{REQUIREMENT}{letter}" for letter in "abcdef"]


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _project(client: TestClient, name: str, framework: str, client_id: str | None = None) -> str:
    if client_id is None:
        client_id = client.post("/api/clients", json={"name": f"{name} client"}).json()["id"]
    response = client.post(
        f"/api/clients/{client_id}/projects",
        json={"name": name, "framework_version_id": framework},
    )
    assert response.status_code == 201, response.text
    return cast(str, response.json()["id"])


def _record(client: TestClient, project: str, assessment: str, record: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/records/{record}")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _save(client: TestClient, assessment: str, record: str, **body: str) -> Any:
    return client.put(f"/api/assessments/{assessment}/determinations/{record}", json=body)


def _requirement_status(client: TestClient, project: str, assessment: str) -> str:
    return cast(str, _record(client, project, assessment, REQUIREMENT)["determination"]["status"])


def test_cmmc_project_opens_all_requirements_and_objectives(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        frameworks = {item["id"] for item in client.get("/api/frameworks").json()}
        assert frameworks == {FRAMEWORK_ID, CMMC_FRAMEWORK_ID}
        project = _project(client, "CMMC 2026", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        workspace = client.get(f"/api/projects/{project}/assessment").json()
        assert workspace["id"] == assessment
        assert workspace["framework"]["declarations"]["presentation_mode"] == (
            "requirement_with_objectives"
        )
        assert "N/A" not in workspace["framework"]["declarations"]["status_set"]
        types: dict[str, int] = {}
        for record in workspace["record_index"]:
            types[record["record_type"]] = types.get(record["record_type"], 0) + 1
            assert record["editable_determination"] == (record["record_type"] == "objective")
        assert types == {"requirement": 110, "objective": 320}
        assert workspace["progress"]["determination_record_count"] == 320
        detail = _record(client, project, assessment, REQUIREMENT)
        assert [child["record_id"] for child in detail["children"]] == OBJECTIVES
        assert detail["determination"]["derived"] is True


def test_requirement_status_derives_from_objectives(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC rollup", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        assert _requirement_status(client, project, assessment) == ""

        observed = "Observed the account list with the administrator."
        for objective in OBJECTIVES[:-1]:
            assert _save(
                client, assessment, objective, status="Met", interview_observation=observed
            ).status_code == 200
        # One objective still blank keeps the requirement blank, never Met.
        assert _requirement_status(client, project, assessment) == ""

        assert _save(client, assessment, OBJECTIVES[-1], status="Pending").status_code == 200
        assert _requirement_status(client, project, assessment) == "Pending"

        assert _save(client, assessment, OBJECTIVES[0], status="Not Met").status_code == 200
        assert _requirement_status(client, project, assessment) == "Not Met"

        assert _save(
            client, assessment, OBJECTIVES[0], status="Met", interview_observation=observed
        ).status_code == 200
        assert _save(
            client, assessment, OBJECTIVES[-1], status="Met", interview_observation=observed
        ).status_code == 200
        assert _requirement_status(client, project, assessment) == "Met"


def test_requirement_edits_and_unsupported_statuses_are_rejected(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC guards", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        derived = _save(client, assessment, REQUIREMENT, status="Pending")
        assert derived.status_code == 422
        assert "derived" in derived.json()["detail"]
        not_applicable = _save(client, assessment, OBJECTIVES[0], status="N/A", na_rationale="x")
        assert not_applicable.status_code == 422
        assert _requirement_status(client, project, assessment) == ""


def test_met_without_evidence_is_evidence_pending_until_evidence_is_mapped(
    tmp_path: Path,
) -> None:
    """Since #141 (ADR 0019 decision 3) Met is not refused at the click; it is
    saved as evidence pending and verified once evidence is mapped. Close and
    issue still require the evidence (see test_issue_141_verified_score.py)."""
    with _client(tmp_path) as client:
        project = _project(client, "CMMC evidence", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        pending = _save(client, assessment, OBJECTIVES[0], status="Met")
        assert pending.status_code == 200, pending.text
        assert pending.json()["verification"] == "evidence_pending"

        artifact = client.post(
            f"/api/projects/{project}/evidence",
            files={"file": ("account-list.txt", b"sanitized evidence", "text/plain")},
        ).json()["id"]
        mapped = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={
                "artifact_id": artifact,
                "record_id": OBJECTIVES[0],
                "rationale": "Lists authorized users.",
            },
        )
        assert mapped.status_code == 201, mapped.text
        verified = _save(client, assessment, OBJECTIVES[0], status="Met")
        assert verified.status_code == 200
        assert verified.json()["verification"] == "verified"


def test_hipaa_unchanged_and_cmmc_ids_isolated(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        shared_client = client.post("/api/clients", json={"name": "Shared"}).json()["id"]
        hipaa = _project(client, "HIPAA 2026", FRAMEWORK_ID, shared_client)
        cmmc = _project(client, "CMMC same client", CMMC_FRAMEWORK_ID, shared_client)
        other = _project(client, "CMMC other client", CMMC_FRAMEWORK_ID)
        hipaa_assessment = create_assessment(client, hipaa)
        cmmc_assessment = create_assessment(client, cmmc)
        other_assessment = create_assessment(client, other)

        hipaa_workspace = client.get(f"/api/projects/{hipaa}/assessment").json()
        assert hipaa_workspace["framework"]["id"] == FRAMEWORK_ID
        assert hipaa_workspace["progress"]["determination_record_count"] == 149
        assert "N/A" in hipaa_workspace["framework"]["declarations"]["status_set"]

        # A CMMC record does not exist in the HIPAA assessment, and vice versa.
        assert client.get(
            f"/api/projects/{hipaa}/assessments/{hipaa_assessment}/records/{OBJECTIVES[0]}"
        ).status_code == 404
        assert _save(client, hipaa_assessment, OBJECTIVES[0], status="Pending").status_code == 404
        assert _save(
            client, cmmc_assessment, "164.308(a)(1)(ii)(A)", status="Pending"
        ).status_code == 404

        # Same-client and cross-client: one project's assessment is not reachable
        # through another project's path.
        for project, foreign in ((cmmc, other_assessment), (other, cmmc_assessment)):
            assert client.get(
                f"/api/projects/{project}/assessments/{foreign}/records/{REQUIREMENT}"
            ).status_code == 404
        assert client.get(
            f"/api/projects/{hipaa}/assessments/{cmmc_assessment}/records/{REQUIREMENT}"
        ).status_code == 404

        assert _save(client, cmmc_assessment, OBJECTIVES[0], status="Pending").status_code == 200
        assert _requirement_status(client, other, other_assessment) == ""

        # The HIPAA-only SRA refuses CMMC. CMMC declares its own close gate (#108),
        # which never applies HIPAA's SRA check.
        assert client.get(f"/api/projects/{cmmc}/sra").status_code == 404
        close = client.get(f"/api/projects/{cmmc}/assessments/{cmmc_assessment}/close-readiness")
        assert close.status_code == 200
        assert close.json()["ready"] is False
        assert "sra_not_declared" not in {b["code"] for b in close.json()["blockers"]}


def test_cmmc_assessment_survives_restart(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC restart", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        assert _save(client, assessment, OBJECTIVES[0], status="Not Met").status_code == 200
    with _client(tmp_path) as client:
        assert _requirement_status(client, project, assessment) == "Not Met"
        assert len(client.get("/api/frameworks").json()) == 2


def test_practitioner_guidance_is_separate_and_never_determines(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        shared_client = client.post("/api/clients", json={"name": "Guidance"}).json()["id"]
        project = _project(client, "CMMC guidance", CMMC_FRAMEWORK_ID, shared_client)
        hipaa = _project(client, "HIPAA guidance", FRAMEWORK_ID, shared_client)
        assessment = create_assessment(client, project)
        hipaa_assessment = create_assessment(client, hipaa)

        objective = _record(client, project, assessment, OBJECTIVES[0])
        guidance = objective["practitioner_guidance"]
        assert "Not DoD or NIST authority" in guidance["provenance"]
        assert guidance["fields"]["assessment_considerations"]
        assert guidance["fields"]["assessment_considerations"] not in objective["record"][
            "regulation_text"
        ]
        assert objective["determination"]["status"] == ""

        requirement = _record(client, project, assessment, REQUIREMENT)
        assert requirement["practitioner_guidance"]["fields"]["c3pao_guidance"]
        assert requirement["determination"]["status"] == ""
        assert client.get(f"/api/projects/{project}/assessment").json()["progress"][
            "resolved_determination_count"
        ] == 0

        hipaa_record = _record(client, hipaa, hipaa_assessment, "164.308(a)(1)(ii)(A)")
        assert hipaa_record["practitioner_guidance"] is None
