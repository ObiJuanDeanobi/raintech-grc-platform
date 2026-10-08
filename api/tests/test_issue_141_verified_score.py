"""Evidence pending, verified and projected SPRS scores, 32 CFR 170.21 checks (Issue #141).

Compliance-conclusion logic (docs/PROJECT_OPERATING_MODEL.md, Test Depth).
Sources, pinned in docs/sources/cmmc-dfars/:
- NIST SP 800-171 DoD Assessment Methodology v1.2.1 (June 24, 2020):
  section 5(b), p. 5 (110 minus each unmet requirement's value); section 5(d),
  p. 6 (5-, 3- and 1-point lists); section 5(e), p. 7 (partial credit for 3.5.3
  and 3.13.11); Annex A, pp. 15 (3.5.3), 18 (3.12.4 "NA"), 19 (3.13.11).
- 32 CFR 170.21(a)(2)(i)-(iii) (eCFR snapshot title-32-part-170-2026-10-06.xml):
  verified score / 110 >= 0.8; only 1-point requirements on a POA&M, except
  SC.L2-3.13.11 at 3 points when encryption is employed but not FIPS-validated;
  six requirements never on a POA&M.
"""

import re
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

OBSERVED = "Synthetic: observed with the administrator."
MINUS = "−"
NEVER_ON_POAM = [
    "AC.L2-3.1.20",
    "AC.L2-3.1.22",
    "CA.L2-3.12.4",
    "PE.L2-3.10.3",
    "PE.L2-3.10.4",
    "PE.L2-3.10.5",
]
# 1-point requirements that may be on a POA&M (32 CFR 170.21(a)(2)(ii)).
ONE_POINT = [
    "AC.L2-3.1.3", "AC.L2-3.1.4", "AC.L2-3.1.6", "AC.L2-3.1.7", "AC.L2-3.1.8",
    "AC.L2-3.1.9", "AC.L2-3.1.10", "AC.L2-3.1.11", "AC.L2-3.1.14", "AC.L2-3.1.15",
    "AC.L2-3.1.21", "AT.L2-3.2.3", "AU.L2-3.3.3", "AU.L2-3.3.4", "AU.L2-3.3.6",
    "AU.L2-3.3.7", "AU.L2-3.3.8", "AU.L2-3.3.9", "CM.L2-3.4.3", "CM.L2-3.4.4",
    "CM.L2-3.4.9", "IA.L2-3.5.4", "IA.L2-3.5.5",
]  # fmt: skip


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _objectives(client: TestClient, project: str) -> dict[str, list[str]]:
    index = client.get(f"/api/projects/{project}/assessment").json()["record_index"]
    by_requirement: dict[str, list[str]] = {}
    for record in index:
        if record["record_type"] == "objective":
            by_requirement.setdefault(record["parent_id"], []).append(record["record_id"])
    return by_requirement


def _save(client: TestClient, assessment: str, record: str, status: str, observed: str = "") -> Any:
    response = client.put(
        f"/api/assessments/{assessment}/determinations/{record}",
        json={"status": status, "interview_observation": observed},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _requirement(
    client: TestClient,
    assessment: str,
    objectives: dict[str, list[str]],
    requirement: str,
    status: str,
    observed: str = "",
) -> None:
    for objective in objectives[requirement]:
        _save(client, assessment, objective, status, observed)


def _all_verified_met(
    client: TestClient, assessment: str, objectives: dict[str, list[str]]
) -> None:
    for requirement in objectives:
        _requirement(client, assessment, objectives, requirement, "Met", OBSERVED)


def _score(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/cmmc-score")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _partial(
    client: TestClient, project: str, assessment: str, requirement: str, level: str
) -> dict[str, Any]:
    response = client.put(
        f"/api/projects/{project}/assessments/{assessment}/requirements/{requirement}"
        "/partial-implementation",
        json={"implementation": level, "rationale": f"Synthetic: {level} implementation."},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _map(client: TestClient, project: str, assessment: str, record: str) -> str:
    artifact = client.post(
        f"/api/projects/{project}/evidence",
        files={"file": (f"{record}.txt", b"synthetic evidence", "text/plain")},
    ).json()["id"]
    mapped = client.post(
        f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
        json={"artifact_id": artifact, "record_id": record, "rationale": "Synthetic."},
    )
    assert mapped.status_code == 201, mapped.text
    return cast(str, mapped.json()["id"])


def _check_arithmetic(figure: dict[str, Any], maximum: int = 110) -> None:
    """The arithmetic string is literal and sums to the shown value."""
    left, right = figure["arithmetic"].split(" = ")
    terms = left.split(f" {MINUS} ")
    assert int(terms[0]) == maximum
    subtracted = [int(term) for term in terms[1:]]
    assert subtracted == [d["points"] for d in figure["deductions"]]
    assert maximum - sum(subtracted) == figure["value"]
    assert int(right.replace(MINUS, "-")) == figure["value"]


def _check(score: dict[str, Any], key: str) -> dict[str, Any]:
    return next(c for c in score["conditional"]["checks"] if c["key"] == key)


def test_met_without_evidence_is_saved_as_evidence_pending_and_verified_by_support(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Pending Met", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project)["IA.L2-3.5.9"]  # one objective
        assert len(objectives) == 1
        objective = objectives[0]
        detail_url = f"/api/projects/{project}/assessments/{assessment}/records"

        saved = _save(client, assessment, objective, "Met")  # no evidence, no observation
        assert saved["status"] == "Met"
        assert saved["verification"] == "evidence_pending"
        states = client.get(f"/api/projects/{project}/assessment").json()["record_states"]
        assert states[objective]["verification"] == "evidence_pending"
        assert states["IA.L2-3.5.9"]["status"] == "Met"
        assert states["IA.L2-3.5.9"]["verification"] == "evidence_pending"
        requirement = client.get(f"{detail_url}/IA.L2-3.5.9").json()
        assert requirement["determination"]["verification"] == "evidence_pending"
        assert requirement["children"][0]["determination"]["verification"] == "evidence_pending"
        pending = _score(client, project, assessment)
        assert pending["evidence_pending"] == ["IA.L2-3.5.9"]
        assert pending["projected"]["value"] - pending["verified"]["value"] == 1

        # Mapping current evidence verifies it and raises the verified score by its weight.
        mapping = _map(client, project, assessment, objective)
        assert client.get(f"{detail_url}/{objective}").json()["determination"][
            "verification"
        ] == "verified"
        verified = _score(client, project, assessment)
        assert verified["verified"]["value"] == pending["verified"]["value"] + 1
        assert verified["projected"]["value"] == pending["projected"]["value"]
        assert verified["evidence_pending"] == []

        # Unmapping the last evidence is allowed and returns the Met to evidence pending.
        removed = client.delete(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/{mapping}"
        )
        assert removed.status_code == 200, removed.text
        assert _score(client, project, assessment)["evidence_pending"] == ["IA.L2-3.5.9"]

        # A documented interview/observation also verifies it.
        assert _save(client, assessment, objective, "Met", OBSERVED)["verification"] == "verified"
        assert _score(client, project, assessment)["evidence_pending"] == []

        # Not Met and Pending carry no verification state (AC-005 unchanged).
        assert _save(client, assessment, objective, "Not Met")["verification"] is None
        assert _save(client, assessment, objective, "Pending")["verification"] is None


def test_requirement_is_verified_only_when_every_objective_is(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Partly verified", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project)["AC.L2-3.1.1"]
        for objective in objectives[:-1]:
            _save(client, assessment, objective, "Met", OBSERVED)
        _save(client, assessment, objectives[-1], "Met")
        states = client.get(f"/api/projects/{project}/assessment").json()["record_states"]
        assert states["AC.L2-3.1.1"]["verification"] == "evidence_pending"
        assert states[objectives[0]]["verification"] == "verified"
        _map(client, project, assessment, objectives[-1])
        states = client.get(f"/api/projects/{project}/assessment").json()["record_states"]
        assert states["AC.L2-3.1.1"]["verification"] == "verified"


def test_hipaa_met_rule_is_unchanged(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "HIPAA unchanged", FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        workspace = client.get(f"/api/projects/{project}/assessment").json()
        record = next(
            r["record_id"]
            for r in workspace["record_index"]
            if r["editable_determination"] and r["designation"] != "addressable"
        )
        refused = client.put(
            f"/api/assessments/{assessment}/determinations/{record}", json={"status": "Met"}
        )
        assert refused.status_code == 422
        assert "Met requires mapped evidence" in refused.text
        assert "met_without_evidence" not in workspace["framework"]["declarations"]


def test_empty_assessment_scores_the_official_minimum_in_both_figures(tmp_path: Path) -> None:
    """Nothing assessed is nothing Met: no score is inflated by work not yet done."""
    with _client(tmp_path) as client:
        project = _project(client, "Empty", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        score = _score(client, project, assessment)
        assert score["verified"]["value"] == score["projected"]["value"] == -203
        assert score["score"] == score["minimum_score"] == -203
        assert score["complete"] is False
        assert len(score["unscored"]) == 110
        assert score["verified"]["arithmetic"].endswith(f"= {MINUS}203")
        _check_arithmetic(score["verified"])
        _check_arithmetic(score["projected"])
        assert score["conditional"]["eligible"] is False


def test_verified_and_projected_scores_on_mixed_evidence(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Mixed", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project)
        _all_verified_met(client, assessment, objectives)
        full = _score(client, project, assessment)
        assert (full["verified"]["value"], full["projected"]["value"]) == (110, 110)
        assert full["verified"]["arithmetic"] == "110 = 110"
        assert full["complete"] is True and full["conditional"]["eligible"] is True

        # 5-point requirement Met without evidence, 3-point Not Met, 1-point Met without evidence.
        _requirement(client, assessment, objectives, "AC.L2-3.1.1", "Met")
        _requirement(client, assessment, objectives, "AC.L2-3.1.19", "Not Met")
        _requirement(client, assessment, objectives, "AC.L2-3.1.3", "Met")
        score = _score(client, project, assessment)
        # Deductions follow catalog order.
        assert score["verified"]["arithmetic"] == f"110 {MINUS} 5 {MINUS} 1 {MINUS} 3 = 101"
        assert score["projected"]["arithmetic"] == f"110 {MINUS} 3 = 107"
        assert score["score"] == score["verified"]["value"] == 101  # headline is verified
        assert score["projected"]["value"] == 107
        assert [
            (d["record_id"], d["points"], d["state"]) for d in score["verified"]["deductions"]
        ] == [
            ("AC.L2-3.1.1", 5, "evidence_pending"),
            ("AC.L2-3.1.3", 1, "evidence_pending"),
            ("AC.L2-3.1.19", 3, "not_met"),
        ]
        assert score["evidence_pending"] == ["AC.L2-3.1.1", "AC.L2-3.1.3"]
        assert score["complete"] is True
        _check_arithmetic(score["verified"])
        _check_arithmetic(score["projected"])
        # Conditional status is judged on the verified score: 5- and 3-point items fail (ii).
        assert _check(score, "minimum_score")["passed"] is True
        assert _check(score, "maximum_points")["passed"] is False
        assert score["conditional"]["eligible"] is False

        # Evidence for the 5-point requirement raises the verified score by 5 (AC-023).
        for objective in objectives["AC.L2-3.1.1"]:
            _map(client, project, assessment, objective)
        after = _score(client, project, assessment)
        assert after["verified"]["value"] == 106
        assert after["projected"]["value"] == 107
        _check_arithmetic(after["verified"])


def test_partial_credit_follows_the_methodology(tmp_path: Path) -> None:
    """Methodology v1.2.1 section 5(e), p. 7; Annex A p. 15 (3.5.3) and p. 19 (3.13.11)."""
    with _client(tmp_path) as client:
        project = _project(client, "Partial", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project)
        _all_verified_met(client, assessment, objectives)

        # Not Met with no implementation level recorded: the full 5, and the input is required.
        _requirement(client, assessment, objectives, "IA.L2-3.5.3", "Not Met")
        unrecorded = _score(client, project, assessment)
        assert unrecorded["verified"]["value"] == 105
        assert unrecorded["partial_inputs_needed"] == ["IA.L2-3.5.3"]
        assert unrecorded["complete"] is False
        # MFA for remote and privileged users only: 3. No MFA for any users: 5.
        assert _partial(client, project, assessment, "IA.L2-3.5.3", "partial")["score"] == 107
        assert _partial(client, project, assessment, "IA.L2-3.5.3", "none")["score"] == 105
        _partial(client, project, assessment, "IA.L2-3.5.3", "partial")
        score = _score(client, project, assessment)
        assert score["verified"]["arithmetic"] == f"110 {MINUS} 3 = 107"
        # 3.5.3 at 3 points is not POA&M-eligible: only 1-point items, except 3.13.11.
        line = next(d for d in score["deductions"] if d["record_id"] == "IA.L2-3.5.3")
        assert line["conditional_poam_allowed"] is False
        assert score["conditional"]["eligible"] is False

        # A Met that is evidence pending counts full value in verified, nothing in projected,
        # even with a stale partial level on file.
        _requirement(client, assessment, objectives, "IA.L2-3.5.3", "Met")
        pending = _score(client, project, assessment)
        assert pending["verified"]["arithmetic"] == f"110 {MINUS} 5 = 105"
        assert pending["projected"]["arithmetic"] == "110 = 110"

        # 3.13.11: encryption employed but not FIPS-validated is 3 points and the one
        # 3-point POA&M exception in 32 CFR 170.21(a)(2)(ii); not employed is 5 and is not.
        _requirement(client, assessment, objectives, "IA.L2-3.5.3", "Met", OBSERVED)
        _requirement(client, assessment, objectives, "SC.L2-3.13.11", "Not Met")
        fips = _partial(client, project, assessment, "SC.L2-3.13.11", "partial")
        assert fips["verified"]["arithmetic"] == f"110 {MINUS} 3 = 107"
        assert fips["conditional"]["eligible"] is True
        none = _partial(client, project, assessment, "SC.L2-3.13.11", "none")
        assert none["verified"]["value"] == 105
        assert _check(none, "maximum_points")["passed"] is False
        assert none["conditional"]["eligible"] is False


def test_conditional_minimum_score_boundary_is_exactly_88(tmp_path: Path) -> None:
    """32 CFR 170.21(a)(2)(i): score / 110 >= 0.8, so 88 passes and 87 fails."""
    with _client(tmp_path) as client:
        project = _project(client, "Boundary", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project)
        _all_verified_met(client, assessment, objectives)
        for requirement in ONE_POINT[:22]:
            _requirement(client, assessment, objectives, requirement, "Not Met")
        at_88 = _score(client, project, assessment)
        assert at_88["verified"]["value"] == 88
        _check_arithmetic(at_88["verified"])
        assert at_88["conditional"]["minimum_score"] == 88
        assert _check(at_88, "minimum_score")["passed"] is True
        assert _check(at_88, "maximum_points")["passed"] is True
        assert _check(at_88, "excluded")["passed"] is True
        assert at_88["conditional"]["eligible"] is True

        _requirement(client, assessment, objectives, ONE_POINT[22], "Not Met")
        at_87 = _score(client, project, assessment)
        assert at_87["verified"]["value"] == 87
        assert _check(at_87, "minimum_score")["passed"] is False
        assert _check(at_87, "maximum_points")["passed"] is True
        assert at_87["conditional"]["eligible"] is False

        # The projected score never decides Conditional status: an evidence-pending Met
        # lifts projected to 88 while verified stays at 87 and still fails.
        _requirement(client, assessment, objectives, ONE_POINT[22], "Met")
        lifted = _score(client, project, assessment)
        assert (lifted["verified"]["value"], lifted["projected"]["value"]) == (87, 88)
        assert _check(lifted, "minimum_score")["passed"] is False
        assert lifted["conditional"]["eligible"] is False


def test_never_on_poam_requirements_block_conditional_status(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Never on POA&M", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project)
        _all_verified_met(client, assessment, objectives)
        passing = _check(_score(client, project, assessment), "excluded")
        assert passing["passed"] is True
        assert passing["source"] == "32 CFR 170.21(a)(2)(iii)"
        assert [item["record_id"] for item in passing["items"]] == NEVER_ON_POAM

        _requirement(client, assessment, objectives, "PE.L2-3.10.3", "Not Met")  # 1 point
        score = _score(client, project, assessment)
        assert score["verified"]["value"] == 109
        failing = _check(score, "excluded")
        assert failing["passed"] is False
        assert {i["record_id"]: i["state"] for i in failing["items"]}["PE.L2-3.10.3"] == "not_met"
        line = next(d for d in score["deductions"] if d["record_id"] == "PE.L2-3.10.3")
        assert line["conditional_poam_allowed"] is False
        assert "170.21(a)(2)(iii)" in line["poam_reason"]
        assert score["conditional"]["eligible"] is False

        # Evidence pending on a never-POA&M requirement also fails: it is not verified Met.
        _requirement(client, assessment, objectives, "PE.L2-3.10.3", "Met")
        assert _check(_score(client, project, assessment), "excluded")["passed"] is False

        # 3.12.4 has no point value (Methodology Annex A p. 18) but blocks completion.
        _requirement(client, assessment, objectives, "PE.L2-3.10.3", "Met", OBSERVED)
        _requirement(client, assessment, objectives, "CA.L2-3.12.4", "Not Met")
        ssp = _score(client, project, assessment)
        assert ssp["verified"]["value"] == 110
        assert ssp["complete"] is False
        assert _check(ssp, "excluded")["passed"] is False


def test_checks_cite_the_pinned_paragraphs(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Citations", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        score = _score(client, project, assessment)
        assert [(c["key"], c["source"]) for c in score["conditional"]["checks"]] == [
            ("minimum_score", "32 CFR 170.21(a)(2)(i)"),
            ("maximum_points", "32 CFR 170.21(a)(2)(ii)"),
            ("excluded", "32 CFR 170.21(a)(2)(iii)"),
        ]
        assert "Methodology v1.2.1" in score["methodology"]
        assert re.search(r"at least 88 of 110", _check(score, "minimum_score")["detail"])


def test_evidence_pending_met_blocks_readiness_close_and_issue(tmp_path: Path) -> None:
    """The #108 close (all 110 Met) still requires every final Met to be verified (AC-004)."""
    from api.tests.test_issue_108_cmmc_close_issue import (
        FAILING,
        _codes,
        _issuable,
        _readiness,
        _sign,
    )
    from api.tests.test_issue_108_cmmc_close_issue import (
        _client as _close_client,
    )
    from api.tests.test_issue_m3_hipaa_issue_backup import _backup

    with _close_client(tmp_path) as client:
        project, assessment, package = _issuable(client, "pending-close")
        assert _readiness(client, project, assessment)["ready"] is True
        _sign(client, project, package["id"])

        # Fieldwork changes the Met to evidence pending after sign-off.
        _save(client, assessment, FAILING, "Met")
        readiness = _readiness(client, project, assessment)
        assert readiness["ready"] is False
        assert "met_evidence_pending" in _codes(readiness)
        blocker = next(b for b in readiness["blockers"] if b["code"] == "met_evidence_pending")
        assert FAILING in blocker["detail"]
        backup = _backup(client, project, package["id"])
        assert backup.status_code == 409
        assert "no longer ready" in backup.text
        issued = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": "none"},
        )
        assert issued.status_code != 201
        assert (
            client.post(f"/api/projects/{project}/assessments/{assessment}/packages").status_code
            != 201
        )

        # Recording the observation verifies it again and clears the blocker.
        _save(client, assessment, FAILING, "Met", OBSERVED)
        assert "met_evidence_pending" not in _codes(_readiness(client, project, assessment))
