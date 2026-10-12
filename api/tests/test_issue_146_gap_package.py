"""The CMMC gap-assessment package, the default CMMC finalize (ticket #146, ADR 0023)."""

import html
import io
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from api.renderers.cmmc import SCOPE_STATEMENT
from api.tests.test_issue_62_versioned_profile import create_project
from api.tests.test_issue_107_cmmc_ssp import OBSERVED, _objectives, _project
from api.tests.test_issue_108_cmmc_close_issue import (
    FAILING,
    REQUIREMENT,
    _approve_ssp,
    _complete_profile,
    _ready_project,
)
from api.tests.test_issue_145_drafts import BANNER, _assert_docx_is_draft
from api.tests.test_issue_m3_hipaa_issue_backup import _app
from api.tests.test_issue_m3_substantive_reopening import _reopen

GAP_KINDS = {"assessment_report", "sprs_worksheet", "poam", "ssp", "evidence_index"}
CLOSE_KINDS = {"assessment_report", "ssp", "poam", "evidence_index"}
NOT_MET = "AC.L2-3.1.1"
PENDING = "AC.L2-3.1.2"
VERIFIED = "AC.L2-3.1.3"


@pytest.fixture(autouse=True)
def _no_double_submit_window(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.issuance as issuance

    monkeypatch.setattr(issuance, "DOUBLE_SUBMIT_SECONDS", 0)


def _decide(
    client: TestClient, assessment: str, objective: str, status: str, observed: str
) -> None:
    response = client.put(
        f"/api/assessments/{assessment}/determinations/{objective}",
        json={"status": status, "interview_observation": observed},
    )
    assert response.status_code == 200, response.text


def _decided(client: TestClient, suffix: str) -> tuple[str, str]:
    """An approved Profile and every objective decided, with gaps.

    AC.L2-3.1.1 is Not Met, AC.L2-3.1.2 is Met with nothing to verify it (evidence
    pending), everything else is Met and verified by a documented observation.
    """
    project, assessment = _project(client, suffix)
    for objective in _objectives(client, project):
        parent = objective["parent_id"]
        if parent == NOT_MET:
            _decide(client, assessment, objective["record_id"], "Not Met", "Synthetic: stale list.")
        elif parent == PENDING:
            _decide(client, assessment, objective["record_id"], "Met", "")
        else:
            _decide(client, assessment, objective["record_id"], "Met", OBSERVED)
    return project, assessment


def _half(client: TestClient, suffix: str) -> tuple[str, str]:
    """Half done: only three requirements decided; everything else is blank."""
    project, assessment = _project(client, suffix)
    for objective in _objectives(client, project):
        parent = objective["parent_id"]
        if parent == NOT_MET:
            _decide(client, assessment, objective["record_id"], "Not Met", "Synthetic: stale list.")
        elif parent == PENDING:
            _decide(client, assessment, objective["record_id"], "Met", "")
        elif parent == VERIFIED:
            _decide(client, assessment, objective["record_id"], "Met", OBSERVED)
    return project, assessment


def _complete(client: TestClient, suffix: str) -> tuple[str, str]:
    """Every requirement Met and verified, POA&M closed, SSP approved, Profile complete."""
    project, assessment, action = _ready_project(client, suffix)
    _decide(client, assessment, FAILING, "Met", OBSERVED)
    closed = client.post(
        f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}"
        f"/poam/{action}/close",
        json={"rationale": "List rebuilt and reviewed."},
    )
    assert closed.status_code == 200, closed.text
    _approve_ssp(client, project, assessment)
    _complete_profile(client, project)
    return project, assessment


def _issue(
    client: TestClient, project: str, assessment: str, package: str | None = None, note: str = ""
) -> Response:
    body: dict[str, Any] = {"actor_id": "johnathan", "note": note}
    if package:
        body["package"] = package
    return client.post(f"/api/projects/{project}/assessments/{assessment}/issue", json=body)


def _score(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/cmmc-score")
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as docx:
        return html.unescape(docx.read("word/document.xml").decode())


def _artifacts(client: TestClient, project: str, package_id: str) -> dict[str, tuple[str, str]]:
    """Each component of an issued package as (file name, readable text), by kind."""
    package = next(
        p for p in client.get(f"/api/projects/{project}/packages").json() if p["id"] == package_id
    )
    result = {}
    for component in package["components"]:
        response = client.get(
            f"/api/projects/{project}/packages/{package_id}/components/{component['id']}"
        )
        assert response.status_code == 200, response.text
        text = (
            _docx_text(response.content)
            if component["filename"].endswith(".docx")
            else response.text
        )
        result[component["kind"]] = (component["filename"], text)
    return result


def _count(db: Path, table: str, where: str = "1=1") -> int:
    with sqlite3.connect(db) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0])


def _lifecycles(client: TestClient, project: str) -> dict[str, str]:
    return {p["id"]: p["lifecycle"] for p in client.get(f"/api/projects/{project}/packages").json()}


def _source(db: Path, package_id: str) -> dict[str, Any]:
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            """SELECT s.source_json FROM generated_packages p
               JOIN source_snapshots s ON s.id = p.source_snapshot_id WHERE p.id = ?""",
            (package_id,),
        ).fetchone()
    result: dict[str, Any] = json.loads(row[0])
    return result


def _rows(worksheet: str) -> dict[str, str]:
    return {line.split(",")[0]: line for line in worksheet.splitlines()}


def test_gap_package_finalizes_with_not_met_work(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-finalize")
        # The readiness close can never clear this assessment; the gap package can.
        close = client.get(f"/api/projects/{project}/assessments/{assessment}/close-readiness")
        assert close.json()["ready"] is False

        issued = _issue(client, project, assessment, note="Gap assessment for the kickoff.")
        assert issued.status_code == 201, issued.text
        body = issued.json()
        assert body["issuance_status"] == "Current" and body["reviewer"] == "Johnathan"
        assert _lifecycles(client, project) == {body["package_id"]: "Issued"}

        artifacts = _artifacts(client, project, body["package_id"])
        assert set(artifacts) == GAP_KINDS
        names = {kind: name for kind, (name, _) in artifacts.items()}
        assert names["assessment_report"] == "CMMC_L2_Gap_Assessment_Report.docx"
        assert names["sprs_worksheet"] == "SPRS_Worksheet_Verified.csv"
        assert names["ssp"] == "System_Security_Plan_DRAFT.docx"  # nothing approved yet
        assert "NOT APPROVED" in artifacts["ssp"][1]

        source = _source(db, body["package_id"])
        assert source["package_type"] == "gap_assessment"
        assert source["readiness"]["package_type"] == "gap_assessment"
        # The snapshot records codes and counts, never blocker wording.
        assert set(source["readiness"]) == {
            "package_type",
            "status",
            "ready",
            "blocking",
            "deferred",
        }
        assert _count(db, "backup_records", "status='complete'") == 1
        assert _count(db, "issuance_snapshots") == 1


def test_undecided_objectives_block_finalize_but_the_draft_still_downloads(
    tmp_path: Path,
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _half(client, "gap-undecided")
        base = f"/api/projects/{project}/assessments/{assessment}"
        refused = _issue(client, project, assessment)
        assert refused.status_code == 409
        groups = {g["key"]: g for g in refused.json()["detail"]["groups"]}
        assert groups["undecided"]["label"] == "Objectives not yet decided"
        assert groups["undecided"]["count"] == 307
        assert "not_met" not in groups  # Not Met is allowed
        checklist = client.get(f"{base}/issue-checklist").json()
        assert checklist["ready"] is False and checklist["package_type"] == "gap_assessment"

        # Pending is an evidence request, not a decision, so it blocks too.
        project2, assessment2 = _decided(client, "gap-pending-objective")
        objective = next(o for o in _objectives(client, project2) if o["parent_id"] == VERIFIED)
        _decide(client, assessment2, objective["record_id"], "Pending", "")
        pending = _issue(client, project2, assessment2)
        assert pending.status_code == 409
        keys = {g["key"] for g in pending.json()["detail"]["groups"]}
        assert keys == {"undecided"}

        # Drafts of incomplete work stay available and say so up front.
        draft = client.get(f"{base}/draft")
        assert draft.status_code == 200, draft.text
        archive = zipfile.ZipFile(io.BytesIO(draft.content))
        report = html.unescape(
            _assert_docx_is_draft(archive.read("DRAFT_CMMC_L2_Gap_Assessment_Report.docx"))
        )
        assert "This assessment is not complete" in report
        assert "307 of 320 objectives not yet assessed" in report
        assert "not overstated by unfinished work" in report
    for table in ("generated_packages", "source_snapshots", "backup_records", "issuance_snapshots"):
        assert _count(db, table) == 0, table


def test_report_is_honest_about_scope_score_checks_and_gaps(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-report")
        score = _score(client, project, assessment)
        body = _issue(client, project, assessment).json()
        report = _artifacts(client, project, body["package_id"])["assessment_report"][1]

        assert "gap assessment, not a C3PAO assessment" in report
        assert "All 320 objectives have been assessed." in report
        assert "This assessment is not complete" not in report
        # Never "certified" or "ready for assessment" outside the explicit denial.
        denial = SCOPE_STATEMENT
        assert denial in report
        remainder = report.replace(denial, "").lower()
        for phrase in (
            "certified",
            "certification ready",
            "ready for assessment",
            "ready for a certification assessment",
            "audit ready",
            "audit-ready",
        ):
            assert phrase not in remainder, phrase
        assert "does not certify the organization" in report
        # Verified score with arithmetic, and the three 170.21 checks with pass or fail.
        assert score["verified"]["arithmetic"] in report
        for key in ("minimum_score", "maximum_points", "excluded"):
            check = next(c for c in score["conditional"]["checks"] if c["key"] == key)
            marker = f"{'PASS' if check['passed'] else 'FAIL'} — {check['source']}"
            assert marker in report, marker
        assert "PASS — 32 CFR 170.21(a)(2)(i)" in report  # 100 of 110
        assert "FAIL — 32 CFR 170.21(a)(2)(ii)" in report  # 5-point requirements
        # NOT MET by family with the failed objective, its notes and the POA&M position.
        assert "Requirements that are Not Met" in report
        assert "AC.L2-3.1.1 Authorized Access Control" in report
        assert "Failed objective AC.L2-3.1.1a" in report
        assert "Synthetic: stale list." in report
        assert "POA&M under 32 CFR 170.21: not eligible" in report
        assert "POA&M item: none yet." in report
        assert "Met, evidence still needed" in report and "AC.L2-3.1.2" in report


def test_only_the_verified_score_is_in_every_artifact_and_the_source(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-verified")
        score = _score(client, project, assessment)
        verified, projected = score["verified"], score["projected"]
        assert projected["value"] > verified["value"]  # the evidence-pending Met is the gap
        body = _issue(client, project, assessment).json()
        artifacts = _artifacts(client, project, body["package_id"])

        assert f"Verified SPRS score,{verified['value']}" in artifacts["sprs_worksheet"][1]
        assert f"Verified SPRS score at issue,{verified['value']}" in artifacts["poam"][1]
        assert verified["arithmetic"] in artifacts["sprs_worksheet"][1]
        assert verified["arithmetic"] in artifacts["assessment_report"][1]
        for name, text in artifacts.values():
            assert projected["arithmetic"] not in text, name
            assert "projected" not in text.lower(), name
        source_json = json.dumps(_source(db, body["package_id"]))
        assert '"projected"' not in source_json
        assert projected["arithmetic"] not in source_json


def test_met_without_evidence_is_a_gap_not_a_block_and_not_verified(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-pending")
        checklist = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        ).json()
        assert checklist["package_type"] == "gap_assessment"
        assert checklist["ready"] is True and checklist["groups"] == []
        warnings = {w["key"]: w for w in checklist["warnings"]}
        assert warnings["met_no_evidence"]["count"] > 0
        assert warnings["gaps_no_poam"]["count"] == 1
        assert warnings["ssp_draft"]["count"] == 1
        assert "not_assessed" not in warnings  # undecided work now blocks instead

        score = _score(client, project, assessment)
        assert PENDING in score["evidence_pending"]
        body = _issue(client, project, assessment).json()
        artifacts = _artifacts(client, project, body["package_id"])
        rows = _rows(artifacts["sprs_worksheet"][1])
        assert "Met, evidence pending (counted as not met)" in rows[PENDING]
        assert "Met (verified)" in rows[VERIFIED]
        deductions = score["verified"]["deductions"]
        weight = next(d["points"] for d in deductions if d["record_id"] == PENDING)
        assert weight and f",{weight}," in rows[PENDING]
        # 170.21(a)(2) is about requirements scored NOT MET.
        assert "n/a until assessed" in rows[PENDING]
        assert rows[NOT_MET].split(",")[-2] in ("Yes", "No")
        assert "Assessment complete,Yes" in artifacts["sprs_worksheet"][1]


def test_warnings_cover_open_poam_items_and_failing_170_21_checks(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-warnings")
        base = f"/api/projects/{project}/assessments/{assessment}/requirements"
        assert client.post(f"{base}/{NOT_MET}/poam", json={"draft": True}).status_code == 201
        checklist = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        ).json()
        warnings = {w["key"]: w for w in checklist["warnings"]}
        assert warnings["poam_open"]["count"] == 1
        assert "1 of them are drafts" in warnings["poam_open"]["detail"]
        assert warnings["conditional_checks"]["count"] >= 1
        assert "gaps_no_poam" not in warnings  # the draft counts as a plan
        assert checklist["ready"] is True


def test_worksheet_explains_partial_credit_and_completeness(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-partial")
        for requirement, level in (("IA.L2-3.5.3", "partial"), ("SC.L2-3.13.11", "none")):
            for objective in _objectives(client, project):
                if objective["parent_id"] == requirement:
                    _decide(client, assessment, objective["record_id"], "Not Met", "Synthetic.")
            response = client.put(
                f"/api/projects/{project}/assessments/{assessment}/requirements/{requirement}"
                "/partial-implementation",
                json={"implementation": level, "rationale": "Synthetic."},
            )
            assert response.status_code == 200, response.text
        body = _issue(client, project, assessment).json()
        worksheet = _artifacts(client, project, body["package_id"])["sprs_worksheet"][1]
        rows = _rows(worksheet)
        assert "Scoring note" in worksheet
        assert (
            "MFA implemented only for remote and privileged users: 3 points, not 5"
            in rows["IA.L2-3.5.3"]
        )
        assert "Encryption not employed: 5 points" in rows["SC.L2-3.13.11"]
        assert "Assessment complete,Yes: every objective is assessed" in worksheet


def test_ssp_does_not_say_implemented_where_the_report_says_evidence_pending(
    tmp_path: Path,
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-ssp")
        body = _issue(client, project, assessment).json()
        ssp = _artifacts(client, project, body["package_id"])["ssp"][1]
        section = ssp.split(f"{PENDING}", 1)[1].split("POA&M:", 1)[0][:600]
        assert "Status: Evidence pending (recorded as Met, not yet verified)" in section
        verified = ssp.split(f"{VERIFIED}", 1)[1][:600]
        assert "Status: Implemented" in verified

        # The readiness close keeps the template mapping: every Met reads Implemented.
        done, done_assessment = _complete(client, "gap-ssp-close")
        issued = _issue(client, done, done_assessment, "readiness_close").json()
        close_ssp = _artifacts(client, done, issued["package_id"])["ssp"][1]
        assert "Evidence pending" not in close_ssp
        assert "Status: Implemented" in close_ssp


def test_poam_lists_every_item_with_status_and_eligibility(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-poam")
        base = f"/api/projects/{project}/assessments/{assessment}/requirements"
        drafted = client.post(f"{base}/{NOT_MET}/poam", json={"draft": True})
        assert drafted.status_code == 201, drafted.text
        title = drafted.json()["poam_items"][0]["title"]
        score = _score(client, project, assessment)
        line = next(d for d in score["deductions"] if d["record_id"] == NOT_MET)
        body = _issue(client, project, assessment).json()
        poam = _artifacts(client, project, body["package_id"])["poam"][1]
        row = next(r for r in poam.splitlines() if r.startswith(NOT_MET))
        assert "Draft" in row and title in row
        assert ("Yes" if line["conditional_poam_allowed"] else "No") in row
        assert line["poam_reason"] in row


def test_failed_backup_blocks_and_leaves_the_prior_final_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance

    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-backup")
        first = _issue(client, project, assessment).json()
        working = issuance._validate_archive
        monkeypatch.setattr(
            issuance,
            "_validate_archive",
            lambda *a, **k: (_ for _ in ()).throw(OSError("disk is full")),
        )
        failed = _issue(client, project, assessment)
        assert failed.status_code == 409
        assert failed.json()["detail"] == (
            "Backup failed: disk is full. Nothing was issued; the last issued version is "
            "still current."
        )
        assert _lifecycles(client, project)[first["package_id"]] == "Issued"
        assert _count(db, "issuance_snapshots") == 1
        assert _count(db, "backup_records", "status='failed'") == 1

        monkeypatch.setattr(issuance, "_validate_archive", working)
        second = _issue(client, project, assessment)
        assert second.status_code == 201, second.text
        assert _lifecycles(client, project)[first["package_id"]] == "Superseded"


def test_hard_gates_answer_409_with_groups_and_write_nothing(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        # The Profile is not approved.
        project = create_project(client, "gap-profile", "cmmc-l2-ag-v2.13")
        started = client.post(f"/api/projects/{project}/start-assessment").json()
        refused = _issue(client, project, started["assessment"]["id"])
        assert refused.status_code == 409
        detail = refused.json()["detail"]
        assert {g["key"] for g in detail["groups"]} >= {"profile"}
        assert detail["message"] == "Fix these before issuing."

        # Evidence that fails its integrity check.
        project, assessment = _decided(client, "gap-evidence")
        artifact = client.post(
            f"/api/projects/{project}/evidence",
            files={"file": ("list.txt", b"synthetic admin list", "text/plain")},
        ).json()
        mapped = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={
                "artifact_id": artifact["id"],
                "record_id": f"{VERIFIED}a",
                "rationale": "Synthetic.",
            },
        )
        assert mapped.status_code == 201, mapped.text
        with sqlite3.connect(db) as connection:
            relative = connection.execute(
                "SELECT relative_path FROM evidence_versions WHERE artifact_id=?", (artifact["id"],)
            ).fetchone()[0]
        (files / relative).write_bytes(b"changed after upload")
        refused = _issue(client, project, assessment)
        assert refused.status_code == 409
        assert "evidence_failed" in {g["key"] for g in refused.json()["detail"]["groups"]}
        checklist = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        ).json()
        assert checklist["ready"] is False
        assert "evidence_failed" in {g["key"] for g in checklist["groups"]}
    for table in ("generated_packages", "source_snapshots", "backup_records", "issuance_snapshots"):
        assert _count(db, table) == 0, table


def test_a_reopened_record_must_be_rechecked_before_a_new_gap_issue(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "gap-reopen")
        first = _issue(client, project, assessment).json()
        reopened = _reopen(client, project, first["package_id"], affected=[f"{VERIFIED}a"])
        assert reopened.status_code == 201, reopened.text
        successor = reopened.json()["successor_assessment_id"]
        blocked = _issue(client, project, successor)
        assert blocked.status_code == 409
        assert "recheck" in {g["key"] for g in blocked.json()["detail"]["groups"]}
        revalidated = client.post(
            f"/api/projects/{project}/assessments/{successor}/records/{VERIFIED}a/revalidate",
            json={"actor_id": "johnathan", "note": "Re-examined."},
        )
        assert revalidated.status_code in (200, 201), revalidated.text
        second = _issue(client, project, successor)
        assert second.status_code == 201, second.text
        lifecycles = _lifecycles(client, project)
        assert lifecycles[first["package_id"]] == "Superseded"
        assert lifecycles[second.json()["package_id"]] == "Issued"
        assert _source(db, first["package_id"])["package_type"] == "gap_assessment"


def test_the_draft_follows_the_choice_and_is_watermarked(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _half(client, "gap-draft")
        url = f"/api/projects/{project}/assessments/{assessment}/draft"
        before = _count(db, "generated_packages"), _count(db, "source_snapshots")

        gap = client.get(url)  # the default
        assert gap.status_code == 200, gap.text
        archive = zipfile.ZipFile(io.BytesIO(gap.content))
        assert sorted(archive.namelist()) == [
            "DRAFT_CMMC_L2_Gap_Assessment_Report.docx",
            "DRAFT_CMMC_POAM.csv",
            "DRAFT_Evidence_Index.csv",
            "DRAFT_SPRS_Worksheet_Verified.csv",
            "DRAFT_System_Security_Plan_DRAFT.docx",
        ]
        for name in archive.namelist():
            if name.endswith(".csv"):
                assert archive.read(name).decode().splitlines()[0] == BANNER, name
        report = _assert_docx_is_draft(archive.read("DRAFT_CMMC_L2_Gap_Assessment_Report.docx"))
        assert "gap assessment, not a C3PAO assessment" in html.unescape(report)
        _assert_docx_is_draft(archive.read("DRAFT_System_Security_Plan_DRAFT.docx"))
        assert client.get(url + "?package=gap_assessment").status_code == 200

        close_draft = client.get(url + "?package=readiness_close")
        assert close_draft.status_code == 200, close_draft.text
        names = sorted(zipfile.ZipFile(io.BytesIO(close_draft.content)).namelist())
        assert names == [
            "DRAFT_CMMC_L2_Assessment_Report.docx",
            "DRAFT_CMMC_POAM_History.csv",
            "DRAFT_Evidence_Index.csv",
            "DRAFT_System_Security_Plan.docx",
        ]
        assert client.get(url + "?package=nonsense").status_code == 422
        # The retired name is not accepted: nothing is stored under it.
        assert client.get(url + "?package=self_assessment").status_code == 422
        # A draft is never stored.
        assert (_count(db, "generated_packages"), _count(db, "source_snapshots")) == before


def test_an_invalid_package_is_422_everywhere_and_hipaa_has_no_choice(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        org = client.post("/api/clients", json={"name": "Client HIPAA"}).json()["id"]
        project = client.post(f"/api/clients/{org}/projects", json={"name": "HIPAA"}).json()["id"]
        assessment = client.post(f"/api/projects/{project}/start-assessment").json()["assessment"]
        base = f"/api/projects/{project}/assessments/{assessment['id']}"
        assert client.get(f"{base}/draft").status_code == 200
        assert client.get(f"{base}/issue-checklist").json()["package_type"] is None
        for query in ("gap_assessment", "readiness_close", "nonsense"):
            assert client.get(f"{base}/draft?package={query}").status_code == 422, query
            assert client.get(f"{base}/issue-checklist?package={query}").status_code == 422, query
            refused = _issue(client, project, assessment["id"], query)
            assert refused.status_code == 422, query
        assert "CMMC projects only" in refused.json()["detail"]

        cmmc, cmmc_assessment = _decided(client, "gap-422")
        cbase = f"/api/projects/{cmmc}/assessments/{cmmc_assessment}"
        assert client.get(f"{cbase}/issue-checklist?package=nonsense").status_code == 422
        assert client.get(f"{cbase}/draft?package=nonsense").status_code == 422
        assert _issue(client, cmmc, cmmc_assessment, "nonsense").status_code == 422
        # A business gate is still 409.
        assert _issue(client, cmmc, cmmc_assessment, "readiness_close").status_code == 409


def test_readiness_close_option_still_needs_every_requirement_met(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _decided(client, "close-gates")
        checklist = client.get(
            f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
            "?package=readiness_close"
        ).json()
        assert checklist["package_type"] == "readiness_close" and checklist["ready"] is False
        keys = {g["key"] for g in checklist["groups"]}
        assert {"not_met", "met_no_evidence", "poam_open"} & keys
        assert "ssp" in keys
        refused = _issue(client, project, assessment, "readiness_close")
        assert refused.status_code == 409
        assert {g["key"] for g in refused.json()["detail"]["groups"]} == keys
        assert _count(db, "generated_packages") == 0

        # The same assessment issues as a gap assessment.
        assert _issue(client, project, assessment, "gap_assessment").status_code == 201

        # With every requirement Met, the readiness close is the unchanged 110 of 110.
        done, done_assessment = _complete(client, "close-complete")
        issued = _issue(client, done, done_assessment, "readiness_close")
        assert issued.status_code == 201, issued.text
        artifacts = _artifacts(client, done, issued.json()["package_id"])
        assert set(artifacts) == CLOSE_KINDS
        assert "110 of 110" in artifacts["assessment_report"][1]
        assert "package_type" not in _source(db, issued.json()["package_id"])


def test_the_checklist_names_the_held_package_type(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _complete(client, "held")
        url = f"/api/projects/{project}/assessments/{assessment}/issue-checklist"
        assert client.get(url).json()["current_issue"] is None
        assert _issue(client, project, assessment, "readiness_close").status_code == 201
        current = client.get(url + "?package=readiness_close").json()["current_issue"]
        assert current["package_type"] == "readiness_close"
        assert current["assessment_id"] == assessment
        # A plain reissue that defaults to the gap choice would be refused, so say why.
        refused = _issue(client, project, assessment)
        assert refused.status_code == 409
        assert "reopen the assessment" in refused.json()["detail"]


def test_issuing_works_across_package_types_and_keeps_every_issue(tmp_path: Path) -> None:
    client, db, files = _app(tmp_path)
    with client:
        project, assessment = _complete(client, "across")
        gap = _issue(client, project, assessment, "gap_assessment", "As a gap assessment.").json()
        # Same data, same kind: a presentation-only reissue supersedes it.
        again = _issue(client, project, assessment, None, "Reissued.")
        assert again.status_code == 201, again.text
        second = again.json()
        assert second["superseded_package_id"] == gap["package_id"]
        assert _source(db, second["package_id"])["package_type"] == "gap_assessment"
        # The other kind needs a reopened assessment, as changed data does.
        refused = _issue(client, project, assessment, "readiness_close")
        assert refused.status_code == 409
        assert "reopen the assessment" in refused.json()["detail"]

        reopened = _reopen(client, project, second["package_id"], affected=[f"{VERIFIED}a"])
        successor = reopened.json()["successor_assessment_id"]
        client.post(
            f"/api/projects/{project}/assessments/{successor}/records/{VERIFIED}a/revalidate",
            json={"actor_id": "johnathan", "note": "Re-examined."},
        )
        _approve_ssp(client, project, successor)  # the SSP is approved per assessment
        final = _issue(client, project, successor, "readiness_close", "Final.")
        assert final.status_code == 201, final.text
        lifecycles = _lifecycles(client, project)
        assert lifecycles[gap["package_id"]] == "Superseded"
        assert lifecycles[second["package_id"]] == "Superseded"
        assert lifecycles[final.json()["package_id"]] == "Issued"
        assert _count(db, "issuance_snapshots") == 3
        # The superseded gap package's files are still there and still as issued.
        assert set(_artifacts(client, project, gap["package_id"])) == GAP_KINDS
        assert (
            "110 of 110"
            in _artifacts(client, project, final.json()["package_id"])["assessment_report"][1]
        )
