"""CMMC official scoring, requirement-level findings, and POA&M (Issue #105)."""

import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

OBSERVED = "Synthetic: observed with the administrator."
ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _objectives(client: TestClient, project: str, assessment: str, requirement: str) -> list[str]:
    detail = client.get(
        f"/api/projects/{project}/assessments/{assessment}/records/{requirement}"
    ).json()
    return [child["record_id"] for child in detail["children"]]


def _set(client: TestClient, assessment: str, record: str, status: str) -> None:
    body = {"status": status, "interview_observation": OBSERVED if status == "Met" else ""}
    response = client.put(f"/api/assessments/{assessment}/determinations/{record}", json=body)
    assert response.status_code == 200, response.text


def _requirement(
    client: TestClient, project: str, assessment: str, requirement: str, status: str
) -> None:
    for objective in _objectives(client, project, assessment, requirement):
        _set(client, assessment, objective, status)


def _score(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/cmmc-score")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _finding(client: TestClient, project: str, assessment: str, requirement: str) -> Any:
    return client.get(
        f"/api/projects/{project}/assessments/{assessment}/requirements/{requirement}/finding"
    ).json()


def _all_requirements(client: TestClient, project: str) -> list[str]:
    workspace = client.get(f"/api/projects/{project}/assessment").json()
    return [r["record_id"] for r in workspace["record_index"] if r["record_type"] == "requirement"]


def _findings_count(tmp_path: Path) -> int:
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        return int(connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0])


def test_score_matches_the_official_model(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC score", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        empty = _score(client, project, assessment)
        # Since #141 the headline is the verified score: nothing assessed is nothing
        # Met, so an empty assessment shows the official minimum, not 110.
        assert (empty["maximum_score"], empty["score"], empty["complete"]) == (110, -203, False)
        assert empty["score"] == empty["minimum_score"]
        assert len(empty["unscored"]) == 110

        requirements = _all_requirements(client, project)
        for requirement in requirements:
            _requirement(client, project, assessment, requirement, "Met")
        assert _score(client, project, assessment)["score"] == 110
        assert _score(client, project, assessment)["complete"] is True

        # 5-, 3-, and 1-point requirements, per 32 CFR 170.24(c)(2)(i)(B).
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        _requirement(client, project, assessment, "AC.L2-3.1.19", "Not Met")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        result = _score(client, project, assessment)
        assert result["score"] == 110 - 5 - 3 - 1
        assert {d["record_id"]: d["points"] for d in result["deductions"]} == {
            "AC.L2-3.1.1": 5,
            "AC.L2-3.1.19": 3,
            "AC.L2-3.1.3": 1,
        }
        assert all(d["source"].startswith("32 CFR 170.24") for d in result["deductions"])
        assert result["conditional"]["eligible"] is False  # 5- and 3-point items


def test_partial_credit_requires_an_explicit_input(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC partial", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for requirement in _all_requirements(client, project):
            _requirement(client, project, assessment, requirement, "Met")
        _requirement(client, project, assessment, "IA.L2-3.5.3", "Not Met")
        blocked = _score(client, project, assessment)
        assert blocked["complete"] is False
        assert blocked["partial_inputs_needed"] == ["IA.L2-3.5.3"]

        path = f"/api/projects/{project}/assessments/{assessment}/requirements"
        assert (
            client.put(
                f"{path}/IA.L2-3.5.3/partial-implementation", json={"implementation": "partial"}
            ).status_code
            == 422
        )
        assert (
            client.put(
                f"{path}/AC.L2-3.1.1/partial-implementation",
                json={"implementation": "partial", "rationale": "x"},
            ).status_code
            == 422
        )
        saved = client.put(
            f"{path}/IA.L2-3.5.3/partial-implementation",
            json={
                "implementation": "partial",
                "rationale": "MFA for remote and privileged users only.",
            },
        )
        assert saved.status_code == 200
        assert (saved.json()["score"], saved.json()["complete"]) == (107, True)
        none = client.put(
            f"{path}/IA.L2-3.5.3/partial-implementation",
            json={"implementation": "none", "rationale": "No MFA for any users."},
        ).json()
        assert none["score"] == 105

        # SC.L2-3.13.11 at 3 points is the one 3-point POA&M exception (32 CFR 170.21).
        _requirement(client, project, assessment, "IA.L2-3.5.3", "Met")
        _requirement(client, project, assessment, "SC.L2-3.13.11", "Not Met")
        conditional = client.put(
            f"{path}/SC.L2-3.13.11/partial-implementation",
            json={"implementation": "partial", "rationale": "Encryption is not FIPS-validated."},
        ).json()
        assert conditional["score"] == 107
        assert conditional["conditional"]["eligible"] is True


def test_missing_ssp_blocks_scoring_and_excluded_items_block_conditional(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC SSP", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for requirement in _all_requirements(client, project):
            _requirement(client, project, assessment, requirement, "Met")
        _requirement(client, project, assessment, "CA.L2-3.12.4", "Not Met")
        result = _score(client, project, assessment)
        assert result["complete"] is False
        assert any("SSP" in blocker for blocker in result["blockers"])
        _requirement(client, project, assessment, "CA.L2-3.12.4", "Met")
        _requirement(client, project, assessment, "PE.L2-3.10.3", "Not Met")  # 1 point, excluded
        excluded = _score(client, project, assessment)
        assert excluded["score"] == 109
        assert excluded["deductions"][0]["conditional_poam_allowed"] is False
        assert excluded["conditional"]["eligible"] is False


def test_one_finding_per_not_met_requirement_with_history(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC findings", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        a, b, c = _objectives(client, project, assessment, "AC.L2-3.1.1")[:3]
        assert _finding(client, project, assessment, "AC.L2-3.1.1") is None

        _set(client, assessment, a, "Not Met")
        _set(client, assessment, a, "Not Met")  # retry
        first = _finding(client, project, assessment, "AC.L2-3.1.1")
        assert [o["record_id"] for o in first["failed_objectives"]] == [a]
        _set(client, assessment, b, "Not Met")  # a newly failed objective joins
        joined = _finding(client, project, assessment, "AC.L2-3.1.1")
        assert joined["finding"]["id"] == first["finding"]["id"]
        assert [o["record_id"] for o in joined["failed_objectives"]] == [a, b]
        assert [e["event"] for e in joined["history"]] == ["opened", "objectives_changed"]
        assert _findings_count(tmp_path) == 1

        # Pending never creates a finding.
        _set(
            client,
            assessment,
            _objectives(client, project, assessment, "AC.L2-3.1.2")[0],
            "Pending",
        )
        assert _finding(client, project, assessment, "AC.L2-3.1.2") is None
        follow_up = _score(client, project, assessment)["follow_up"]
        assert follow_up[0]["requirement_id"] == "AC.L2-3.1.2"
        assert follow_up[0]["kind"] == "evidence_request"
        pending_poam = client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/AC.L2-3.1.2/poam",
            json={"title": "Should be refused"},
        )
        assert pending_poam.status_code == 409

        poam = client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/AC.L2-3.1.1/poam",
            json={"title": "Maintain the authorized user list", "description": "Quarterly review."},
        )
        assert poam.status_code == 201, poam.text
        assert [item["title"] for item in poam.json()["poam_items"]] == [
            "Maintain the authorized user list"
        ]

        # Clearing keeps the finding and its history; failing again reuses it.
        _set(client, assessment, a, "Pending")
        _set(client, assessment, b, "Pending")
        cleared = _finding(client, project, assessment, "AC.L2-3.1.1")
        assert cleared["history"][-1]["event"] == "requirement_cleared"
        _set(client, assessment, c, "Not Met")
        again = _finding(client, project, assessment, "AC.L2-3.1.1")
        assert again["finding"]["id"] == first["finding"]["id"]
        assert _findings_count(tmp_path) == 1

        # The objective-level HIPAA reconciliation path is closed for CMMC.
        refused = client.put(
            f"/api/projects/{project}/assessments/{assessment}/records/{c}/reconciliation",
            json={"outcome": "not_needed", "rationale": "x"},
        )
        assert refused.status_code == 409

    with _client(tmp_path) as client:
        assert (
            _finding(client, project, assessment, "AC.L2-3.1.1")["finding"]["id"]
            == (first["finding"]["id"])
        )
        assert _findings_count(tmp_path) == 1


def test_finding_carries_to_a_successor_revision(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC successor", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objective = _objectives(client, project, assessment, "AC.L2-3.1.1")[0]
        _set(client, assessment, objective, "Not Met")
        original = _finding(client, project, assessment, "AC.L2-3.1.1")["finding"]["id"]
        successor = client.post(
            f"/api/projects/{project}/assessments/{assessment}/successor",
            json={"actor_id": "johnathan", "reason": "Synthetic reassessment."},
        )
        assert successor.status_code == 201, successor.text
        new = successor.json()["id"]
        _set(client, new, objective, "Not Met")
        carried = _finding(client, project, new, "AC.L2-3.1.1")
        assert carried["finding"]["id"] == original
        assert _findings_count(tmp_path) == 1


def test_scoring_isolation_and_hipaa_unchanged(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        hipaa = _project(client, "HIPAA", FRAMEWORK_ID)
        cmmc = _project(client, "CMMC", CMMC_FRAMEWORK_ID)
        hipaa_assessment = create_assessment(client, hipaa)
        cmmc_assessment = create_assessment(client, cmmc)
        assert (
            client.get(
                f"/api/projects/{hipaa}/assessments/{hipaa_assessment}/cmmc-score"
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/projects/{hipaa}/assessments/{cmmc_assessment}/cmmc-score"
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/projects/{cmmc}/assessments/{cmmc_assessment}/requirements/AC.L2-3.1.1a/finding"
            ).status_code
            == 404
        )


def test_migration_cycle_and_downgrade_guard(tmp_path: Path) -> None:
    database = tmp_path / "workspace.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(tmp_path / "files"))
    command.upgrade(config, "head")
    command.downgrade(config, "0015")
    command.upgrade(config, "head")
    with _client(tmp_path) as client:
        project = _project(client, "CMMC guard", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _set(
            client,
            assessment,
            _objectives(client, project, assessment, "AC.L2-3.1.1")[0],
            "Not Met",
        )
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM requirement_finding_events")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE requirement_findings SET record_id = 'x'")
    with pytest.raises(RuntimeError, match="finding history"):
        command.downgrade(config, "0015")
