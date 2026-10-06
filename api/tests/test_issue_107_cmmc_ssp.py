"""CMMC System Security Plan: generate, edit, approve, freeze, export (Issue #107)."""

import io
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_62_versioned_profile import (
    create_project,
    lifecycle_payload,
    profile_payload,
)

OBSERVED = "Synthetic: observed with the administrator."


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _project(
    client: TestClient, suffix: str, framework: str = CMMC_FRAMEWORK_ID
) -> tuple[str, str]:
    project = create_project(client, suffix, framework)
    draft = client.get(f"/api/projects/{project}/profile").json()["versions"][0]
    assert (
        client.put(
            f"/api/projects/{project}/profile/versions/{draft['id']}",
            json=profile_payload(draft["content_revision"]),
        ).status_code
        == 200
    )
    for status in ("Reviewed", "Approved"):
        assert (
            client.post(
                f"/api/projects/{project}/profile/versions/{draft['id']}/lifecycle",
                json=lifecycle_payload(client, project, draft["id"], status),
            ).status_code
            == 201
        )
    client.post(f"/api/projects/{project}/profile-readiness/acknowledgement")
    client.post(
        f"/api/projects/{project}/profile-readiness/transitions",
        json={"next_state": "Intake complete", "decision_note": "ready"},
    )
    assessment = client.post(f"/api/projects/{project}/assessments").json()["id"]
    return project, assessment


def _objectives(client: TestClient, project: str) -> list[dict[str, Any]]:
    workspace = client.get(f"/api/projects/{project}/assessment").json()
    return [r for r in workspace["record_index"] if r["record_type"] == "objective"]


def _assess_all(client: TestClient, project: str, assessment: str, failing: str = "") -> None:
    for objective in _objectives(client, project):
        status = "Not Met" if objective["record_id"] == failing else "Met"
        body = {"status": status, "interview_observation": OBSERVED if status == "Met" else ""}
        response = client.put(
            f"/api/assessments/{assessment}/determinations/{objective['record_id']}", json=body
        )
        assert response.status_code == 200, response.text


def test_generation_fails_visibly_until_every_requirement_is_resolved(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _project(client, "ssp-blocked")
        refused = client.post(f"/api/projects/{project}/assessments/{assessment}/ssp")
        assert refused.status_code == 409
        assert "110 requirement(s) are not Met or Not Met" in str(refused.json()["detail"])
        assert client.get(f"/api/projects/{project}/assessments/{assessment}/ssp").json() is None


def test_generate_edit_approve_freeze_and_export(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _project(client, "ssp")
        _assess_all(client, project, assessment, failing="AC.L2-3.1.1a")
        client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/AC.L2-3.1.1/poam",
            json={"title": "Rebuild the authorized user list"},
        )
        generated = client.post(f"/api/projects/{project}/assessments/{assessment}/ssp")
        assert generated.status_code == 201, generated.text
        ssp = generated.json()
        assert ssp["template_version"] == "cmmc-ssp-v1"
        requirements = {r["record_id"]: r for r in ssp["source"]["requirements"]}
        assert len(requirements) == 110
        assert requirements["AC.L2-3.1.1"]["status"] == "Planned to be Implemented"
        assert requirements["AC.L2-3.1.1"]["poam_items"] == ["Rebuild the authorized user list"]
        assert requirements["AC.L2-3.1.2"]["status"] == "Implemented"
        assert OBSERVED in ssp["latest"]["content"]["requirements"]["AC.L2-3.1.2"]["implementation"]
        assert set(ssp["missing_for_approval"]) >= {"system_description", "environment_narrative"}

        blocked = client.post(f"/api/projects/{project}/ssp/{ssp['id']}/approve")
        assert blocked.status_code == 409

        edited = client.put(
            f"/api/projects/{project}/ssp/{ssp['id']}",
            json={
                "system_description": "Synthetic enclave for contract deliverables.",
                "environment_narrative": "Synthetic cloud tenant and managed endpoints.",
                "requirements": {"AC.L2-3.1.1": "Planned: quarterly user list review (see POA&M)."},
                "note": "Filled narrative sections.",
            },
        )
        assert edited.status_code == 200
        assert edited.json()["latest"]["version_number"] == 2
        assert [v["version_number"] for v in edited.json()["versions"]] == [1, 2]
        assert (
            client.put(
                f"/api/projects/{project}/ssp/{ssp['id']}",
                json={"requirements": {"XX.L2-9.9.9": "x"}},
            ).status_code
            == 422
        )

        approved = client.post(f"/api/projects/{project}/ssp/{ssp['id']}/approve")
        assert approved.status_code == 200, approved.text
        assert approved.json()["approval"]["approver_id"] == "johnathan"
        frozen = client.put(
            f"/api/projects/{project}/ssp/{ssp['id']}", json={"system_description": "late"}
        )
        assert frozen.status_code == 409
        assert client.post(f"/api/projects/{project}/ssp/{ssp['id']}/approve").status_code == 409

        exported = client.get(f"/api/projects/{project}/ssp/{ssp['id']}/versions/2/docx")
        assert exported.status_code == 200
        again = client.get(f"/api/projects/{project}/ssp/{ssp['id']}/versions/2/docx")
        assert exported.content == again.content  # deterministic delivery copy
        text = zipfile.ZipFile(io.BytesIO(exported.content)).read("word/document.xml").decode()
        assert "Synthetic enclave for contract deliverables." in text
        assert "Planned to be Implemented" in text and "Not Applicable" not in text
        assert "approved" in text
        assert (
            client.get(f"/api/projects/{project}/ssp/{ssp['id']}/versions/9/docx").status_code
            == 404
        )


def test_ssp_rows_are_immutable_and_isolated(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _project(client, "ssp-iso")
        other, _ = _project(client, "ssp-other")
        hipaa, hipaa_assessment = _project(client, "ssp-hipaa", FRAMEWORK_ID)
        _assess_all(client, project, assessment)
        ssp = client.post(f"/api/projects/{project}/assessments/{assessment}/ssp").json()
        assert (
            client.put(
                f"/api/projects/{other}/ssp/{ssp['id']}", json={"system_description": "x"}
            ).status_code
            == 404
        )
        assert client.post(f"/api/projects/{other}/ssp/{ssp['id']}/approve").status_code == 404
        assert (
            client.get(f"/api/projects/{other}/ssp/{ssp['id']}/versions/1/docx").status_code == 404
        )
        assert (
            client.post(f"/api/projects/{hipaa}/assessments/{hipaa_assessment}/ssp").status_code
            == 404
        )
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        for statement in (
            "UPDATE ssp_versions SET note = 'x'",
            "DELETE FROM ssp_documents",
            "UPDATE ssp_documents SET source_json = '{}'",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)


def test_template_drift_is_refused(tmp_path: Path) -> None:
    from fastapi import HTTPException

    from api import ssp

    root = tmp_path / "repo"
    (root / ssp.TEMPLATE_PATH).parent.mkdir(parents=True)
    source = Path(__file__).resolve().parents[2] / ssp.TEMPLATE_PATH
    (root / ssp.TEMPLATE_PATH).write_bytes(source.read_bytes() + b" ")
    with pytest.raises(HTTPException):
        ssp.load_template(root)
    assert ssp.load_template(source.parents[4])["template_version"] == "cmmc-ssp-v1"
