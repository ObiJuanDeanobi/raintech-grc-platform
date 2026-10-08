"""Requirement-list markers on the assessment workspace (Issue #140).

``record_states`` is a read-only projection: objective status, derived
requirement status (same rollup as the record detail), evidence counts and open
POA&M counts. It must agree with the record detail and stay project-scoped.
"""

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

REQUIREMENT = "AC.L2-3.1.1"
OBJECTIVES = [f"{REQUIREMENT}{letter}" for letter in "abcdef"]
OBSERVED = "Observed the account list with the administrator."


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


def _states(client: TestClient, project: str) -> dict[str, dict[str, Any]]:
    response = client.get(f"/api/projects/{project}/assessment")
    assert response.status_code == 200, response.text
    return cast(dict[str, dict[str, Any]], response.json()["record_states"])


def _save(client: TestClient, assessment: str, record: str, **body: str) -> None:
    response = client.put(f"/api/assessments/{assessment}/determinations/{record}", json=body)
    assert response.status_code == 200, response.text


def _detail_status(client: TestClient, project: str, assessment: str, record: str) -> str:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/records/{record}")
    return cast(str, response.json()["determination"]["status"])


def test_record_states_follow_determinations_evidence_and_poam(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC markers", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        states = _states(client, project)
        assert len(states) == 430
        assert states[REQUIREMENT] == {"status": "", "evidence_count": 0, "open_poam_count": 0}

        for objective in OBJECTIVES:
            _save(client, assessment, objective, status="Met", interview_observation=OBSERVED)
        states = _states(client, project)
        assert states[OBJECTIVES[0]]["status"] == "Met"
        assert states[REQUIREMENT]["status"] == "Met"

        _save(client, assessment, OBJECTIVES[1], status="Pending")
        assert _states(client, project)[REQUIREMENT]["status"] == "Pending"
        _save(client, assessment, OBJECTIVES[2], status="Not Met")
        states = _states(client, project)
        assert states[REQUIREMENT]["status"] == "Not Met"
        # The projection agrees with the authoritative record detail.
        assert states[REQUIREMENT]["status"] == _detail_status(
            client, project, assessment, REQUIREMENT
        )

        artifact = client.post(
            f"/api/projects/{project}/evidence",
            files={"file": ("account-list.txt", b"synthetic evidence", "text/plain")},
        ).json()["id"]
        mapped = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={"artifact_id": artifact, "record_id": OBJECTIVES[0], "rationale": "List."},
        )
        assert mapped.status_code == 201, mapped.text
        assert _states(client, project)[OBJECTIVES[0]]["evidence_count"] == 1

        poam = client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}/poam",
            json={"title": "Maintain the authorized user list"},
        )
        assert poam.status_code == 201, poam.text
        assert _states(client, project)[REQUIREMENT]["open_poam_count"] == 1


def test_record_states_are_project_scoped_and_hipaa_derives(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        shared = client.post("/api/clients", json={"name": "Shared"}).json()["id"]
        first = _project(client, "CMMC A", CMMC_FRAMEWORK_ID, shared)
        same_client = _project(client, "CMMC B", CMMC_FRAMEWORK_ID, shared)
        other_client = _project(client, "CMMC C", CMMC_FRAMEWORK_ID)
        hipaa = _project(client, "HIPAA", FRAMEWORK_ID, shared)
        first_assessment = create_assessment(client, first)
        create_assessment(client, same_client)
        create_assessment(client, other_client)
        create_assessment(client, hipaa)

        _save(client, first_assessment, OBJECTIVES[0], status="Not Met")
        assert _states(client, first)[REQUIREMENT]["status"] == "Not Met"
        for project in (same_client, other_client):
            assert _states(client, project)[REQUIREMENT]["status"] == ""
            assert _states(client, project)[OBJECTIVES[0]]["status"] == ""

        hipaa_states = _states(client, hipaa)
        assert hipaa_states
        assert all(state["status"] == "" for state in hipaa_states.values())


def test_statement_and_objective_notes_reach_the_next_ssp_draft(tmp_path: Path) -> None:
    """The requirement view saves the implementation statement as the
    requirement's record note and per-objective notes as labelled text; SSP
    generation drafts the implementation from both, without a new SSP version
    per keystroke (no SSP exists while they are typed)."""
    from api.tests.test_issue_107_cmmc_ssp import _assess_all
    from api.tests.test_issue_107_cmmc_ssp import _project as _ssp_project

    with _client(tmp_path) as client:
        project, assessment = _ssp_project(client, "ssp-140")
        statement = "Synthetic: accounts are provisioned only through the HR ticket."
        objective_note = (
            "Examine: Synthetic access policy v3.\nTest: Disabled account cannot log in."
        )
        for record, note in ((REQUIREMENT, statement), (OBJECTIVES[0], objective_note)):
            saved = client.put(
                f"/api/assessments/{assessment}/records/{record}/note", json={"note": note}
            )
            assert saved.status_code == 200, saved.text
        assert client.get(f"/api/projects/{project}/assessments/{assessment}/ssp").json() is None
        _assess_all(client, project, assessment)
        generated = client.post(f"/api/projects/{project}/assessments/{assessment}/ssp")
        assert generated.status_code == 201, generated.text
        drafted = generated.json()["latest"]["content"]["requirements"][REQUIREMENT][
            "implementation"
        ]
        assert drafted.startswith(statement)
        assert "3.1.1[a]: Examine: Synthetic access policy v3." in drafted
        assert "Test: Disabled account cannot log in." in drafted
        assert [v["version_number"] for v in generated.json()["versions"]] == [1]
