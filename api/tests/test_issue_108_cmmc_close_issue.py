"""CMMC readiness close gate and standard package issuance (Issue #108)."""

import io
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_107_cmmc_ssp import OBSERVED, _assess_all, _project
from api.tests.test_issue_m3_hipaa_review import _package, _transition
from api.tests.test_issue_m3_presentation_correction import _correct, _issue

FAILING = "AC.L2-3.1.1a"
REQUIREMENT = "AC.L2-3.1.1"


def _client(tmp_path: Path) -> TestClient:
    files = tmp_path / "files"
    return TestClient(
        create_app(
            database_path=tmp_path / "workspace.db",
            storage_path=files,
            backup_path=files / "backups",
        )
    )


def _sign(client: TestClient, project: str, package_id: str) -> None:
    confirmations = {
        "assessment_report": True,
        "ssp": True,
        "poam": True,
        "evidence_index": True,
        "__source": True,
    }
    for state in ("In Review", "Reviewed", "Ready to issue"):
        response = _transition(
            client, project, package_id, state, component_confirmations=confirmations
        )
        assert response.status_code == 201, response.text


def _readiness(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    return dict(
        client.get(f"/api/projects/{project}/assessments/{assessment}/close-readiness").json()
    )


def _codes(readiness: dict[str, Any]) -> set[str]:
    return {b["code"] for b in readiness["blockers"]}


def _approve_ssp(client: TestClient, project: str, assessment: str) -> None:
    ssp = client.post(f"/api/projects/{project}/assessments/{assessment}/ssp")
    assert ssp.status_code == 201, ssp.text
    client.put(
        f"/api/projects/{project}/ssp/{ssp.json()['id']}",
        json={
            "system_description": "Synthetic enclave.",
            "environment_narrative": "Synthetic tenant.",
        },
    )
    assert client.post(f"/api/projects/{project}/ssp/{ssp.json()['id']}/approve").status_code == 200


def _ready_project(client: TestClient, suffix: str) -> tuple[str, str, str]:
    """A CMMC project whose one failed objective was remediated and its POA&M item closed."""
    project, assessment = _project(client, suffix)
    _assess_all(client, project, assessment, failing=FAILING)
    base = f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}"
    poam = client.post(f"{base}/poam", json={"title": "Rebuild the authorized user list"})
    action = poam.json()["poam_items"][0]["id"]
    return project, assessment, action


def test_each_gate_condition_blocks_independently(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, action = _ready_project(client, "gates")
        base = f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}"
        codes = _codes(_readiness(client, project, assessment))
        assert {"determination_not_final", "poam_open", "ssp_not_approved"} <= codes
        assert "profile_not_complete" in codes
        assert "sra_not_declared" not in codes  # SRA is HIPAA-only

        early = client.post(f"{base}/poam/{action}/close", json={"rationale": "Fixed."})
        assert early.status_code == 409  # requirement still Not Met
        client.put(
            f"/api/assessments/{assessment}/determinations/{FAILING}",
            json={"status": "Met", "interview_observation": OBSERVED},
        )
        assert client.post(f"{base}/poam/{action}/close", json={"rationale": ""}).status_code == 422
        closed = client.post(
            f"{base}/poam/{action}/close", json={"rationale": "List rebuilt and reviewed."}
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["poam_items"][0]["status"] == "Closed"
        codes = _codes(_readiness(client, project, assessment))
        assert "poam_open" not in codes and "determination_not_final" not in codes
        assert "ssp_not_approved" in codes

        _approve_ssp(client, project, assessment)
        assert "ssp_not_approved" not in _codes(_readiness(client, project, assessment))
        refused = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert refused.status_code != 201  # the Profile is still not complete
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM generated_packages").fetchone()[0] == 0


def _complete_profile(client: TestClient, project: str) -> None:
    response = client.post(
        f"/api/projects/{project}/profile-readiness/transitions",
        json={
            "next_state": "Profile complete",
            "decision_note": "Ready for governed generation.",
            "reviewed_by": "Reviewer",
            "approval_evidence": "Approved Profile lifecycle event.",
        },
    )
    assert response.status_code == 201, response.text


def _issuable(client: TestClient, suffix: str) -> tuple[str, str, dict[str, Any]]:
    project, assessment, action = _ready_project(client, suffix)
    client.put(
        f"/api/assessments/{assessment}/determinations/{FAILING}",
        json={"status": "Met", "interview_observation": OBSERVED},
    )
    client.post(
        f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}"
        f"/poam/{action}/close",
        json={"rationale": "List rebuilt and reviewed."},
    )
    _approve_ssp(client, project, assessment)
    _complete_profile(client, project)
    readiness = _readiness(client, project, assessment)
    assert readiness["ready"], readiness["blockers"]
    return project, assessment, _package(client, project, assessment)


def test_standard_package_reviews_backs_up_issues_and_corrects(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, package = _issuable(client, "issue")
        kinds = {c["kind"]: c for c in package["manifest"]["components"]}
        assert set(kinds) == {"assessment_report", "ssp", "poam", "evidence_index"}
        assert package["manifest"]["template_version"] == "cmmc-v1"

        component = client.get(
            f"/api/projects/{project}/packages/{package['id']}/components/{kinds['ssp']['id']}"
        )
        assert component.status_code == 200
        ssp_text = zipfile.ZipFile(io.BytesIO(component.content)).read("word/document.xml").decode()
        assert "Synthetic enclave." in ssp_text and "approved" in ssp_text
        report = client.get(
            f"/api/projects/{project}/packages/{package['id']}/components/"
            f"{kinds['assessment_report']['id']}"
        )
        report_text = zipfile.ZipFile(io.BytesIO(report.content)).read("word/document.xml").decode()
        assert "110 of 110" in report_text
        poam = client.get(
            f"/api/projects/{project}/packages/{package['id']}/components/{kinds['poam']['id']}"
        )
        assert "List rebuilt and reviewed." in poam.text and "Closed" in poam.text

        # Issue needs the exact-package sign-off and a backup.
        early = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": "missing"},
        )
        assert early.status_code != 201
        _sign(client, project, package["id"])
        issued = _issue(client, project, package["id"])
        assert issued.status_code == 201, issued.text

        corrected = _correct(client, project, package["id"], reason="Fix report title spacing.")
        assert corrected.status_code == 201, corrected.text
        new_package = corrected.json()["package"]["id"]
        _sign(client, project, new_package)
        assert _issue(client, project, new_package).status_code == 201
    with _client(tmp_path) as client:  # restart
        listed = client.get(f"/api/projects/{project}/packages").json()
        assert [p["id"] for p in listed if p.get("issuance_status") == "Current"] == [new_package]
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM current_issuances WHERE project_id = ?", (project,)
            ).fetchone()[0]
            == 1
        )


def test_isolation_and_hipaa_unchanged(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, package = _issuable(client, "iso")
        other, _, _ = _ready_project(client, "iso-other")
        assert (
            client.get(
                f"/api/projects/{other}/packages/{package['id']}/components/"
                f"{package['manifest']['components'][0]['id']}"
            ).status_code
            == 404
        )
        assert client.post(
            f"/api/projects/{other}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": "x"},
        ).status_code in (404, 409)


def test_substantive_reopening_reissues_with_a_fresh_ssp(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, package = _issuable(client, "reopen")
        _sign(client, project, package["id"])
        assert _issue(client, project, package["id"]).status_code == 201
        reopened = client.post(
            f"/api/projects/{project}/packages/{package['id']}/reopen",
            json={
                "actor_id": "johnathan",
                "classification": "substantive",
                "affected_record_ids": ["AC.L2-3.1.2a"],
                "rationale": "Evidence for transaction control was superseded.",
            },
        )
        assert reopened.status_code == 201, reopened.text
        successor = reopened.json()["successor_assessment_id"]
        codes = _codes(_readiness(client, project, successor))
        assert {"needs_revalidation", "ssp_not_approved"} <= codes
        assert (
            client.post(
                f"/api/projects/{project}/assessments/{successor}/records/AC.L2-3.1.2a/revalidate",
                json={"actor_id": "johnathan", "note": "Re-examined with current evidence."},
            ).status_code
            == 201
        )
        _approve_ssp(client, project, successor)
        assert _readiness(client, project, successor)["ready"]
        fresh = _package(client, project, successor)
        _sign(client, project, fresh["id"])
        assert _issue(client, project, fresh["id"]).status_code == 201
        listed = {p["id"]: p for p in client.get(f"/api/projects/{project}/packages").json()}
        assert listed[package["id"]]["issuance_status"] == "Superseded"
        assert listed[fresh["id"]]["issuance_status"] == "Current"


def test_poam_closure_migration_cycle_and_guard(tmp_path: Path) -> None:
    import pytest
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{(tmp_path / 'workspace.db').as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(tmp_path / "files"))
    command.upgrade(config, "head")
    command.downgrade(config, "0019")
    command.upgrade(config, "head")
    with _client(tmp_path) as client:
        project, assessment, action = _ready_project(client, "migrate")
        client.put(
            f"/api/assessments/{assessment}/determinations/{FAILING}",
            json={"status": "Met", "interview_observation": OBSERVED},
        )
        closed = client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}"
            f"/poam/{action}/close",
            json={"rationale": "Verified."},
        )
        assert closed.status_code == 200
    with (
        sqlite3.connect(tmp_path / "workspace.db") as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute("DELETE FROM poam_closures")
    with pytest.raises(RuntimeError, match="POA&M closures exist"):
        command.downgrade(config, "0019")
