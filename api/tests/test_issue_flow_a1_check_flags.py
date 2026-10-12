"""170.21 checks that have already failed on decided work show red (ADR 0022, lead-approved).

Before every requirement is decided a check reads "Not yet evaluated", unless decided
items already make it impossible to pass: then it names the decided item. The flags are
display data computed outside the snapshotted score; no figure changes.
"""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_105_cmmc_scoring_findings import (
    _all_requirements,
    _client,
    _objectives,
    _requirement,
    _score,
)
from api.tests.test_issue_m3_active_assessment_backend import create_assessment


def _setup(client: TestClient, name: str) -> tuple[str, str]:
    project = _project(client, name, CMMC_FRAMEWORK_ID)
    return project, create_assessment(client, project)


def _flags(score: dict[str, Any]) -> dict[str, dict[str, str]]:
    return dict(score["check_flags"])


def _excluded(score: dict[str, Any]) -> list[str]:
    checks = {check["key"]: check for check in score["conditional"]["checks"]}
    return [item["record_id"] for item in checks["excluded"]["items"]]


def _lines(score: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {line["record_id"]: line for line in score["deductions"]}


def test_a_blank_project_is_all_grey(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags blank")
        score = _score(client, project, assessment)
        assert score["started"] is False and score["all_decided"] is False
        assert {key: flag["state"] for key, flag in _flags(score).items()} == {
            "minimum_score": "not_evaluated",
            "maximum_points": "not_evaluated",
            "excluded": "not_evaluated",
        }


def test_a_decided_not_met_on_a_never_poam_requirement_fails_that_check_only(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags excluded")
        excluded = _excluded(_score(client, project, assessment))
        assert "AC.L2-3.1.20" in excluded
        _requirement(client, project, assessment, "AC.L2-3.1.20", "Not Met")
        flags = _flags(_score(client, project, assessment))
        assert flags["excluded"]["state"] == "failed"
        assert "AC.L2-3.1.20 is decided Not Met" in flags["excluded"]["reason"]
        assert flags["minimum_score"]["state"] == "not_evaluated"


def test_a_decided_not_met_worth_more_than_one_point_fails_the_poam_points_check(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags points")
        score = _score(client, project, assessment)
        one_point = next(
            requirement
            for requirement in _all_requirements(client, project)
            if requirement not in _excluded(score)
            and _lines(score)[requirement]["points"] == 1
        )
        _requirement(client, project, assessment, one_point, "Not Met")
        assert _flags(_score(client, project, assessment))["maximum_points"]["state"] == (
            "not_evaluated"
        )
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        flags = _flags(_score(client, project, assessment))
        assert flags["maximum_points"]["state"] == "failed"
        assert "AC.L2-3.1.1 is decided Not Met" in flags["maximum_points"]["reason"]
        assert one_point not in flags["maximum_points"]["reason"]


def test_the_minimum_score_check_fails_when_even_the_best_case_is_below_88(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags minimum")
        score = _score(client, project, assessment)
        five_point = [
            requirement
            for requirement in _all_requirements(client, project)
            if requirement not in _excluded(score) and _lines(score)[requirement]["points"] == 5
        ]
        for requirement in five_point[:4]:  # best case 110 - 20 = 90
            _requirement(client, project, assessment, requirement, "Not Met")
        assert _flags(_score(client, project, assessment))["minimum_score"]["state"] == (
            "not_evaluated"
        )
        _requirement(client, project, assessment, five_point[4], "Not Met")  # 110 - 25 = 85
        flags = _flags(_score(client, project, assessment))
        assert flags["minimum_score"]["state"] == "failed"
        assert "85" in flags["minimum_score"]["reason"] and "88" in flags["minimum_score"]["reason"]


def test_evidence_pending_met_never_fails_a_check_early(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags pending")
        # Met with no evidence or observation is evidence pending, not a decided failure.
        for excluded in ("AC.L2-3.1.20", "AC.L2-3.1.1"):
            for objective in _objectives(client, project, assessment, excluded):
                response = client.put(
                    f"/api/assessments/{assessment}/determinations/{objective}",
                    json={"status": "Met", "interview_observation": ""},
                )
                assert response.status_code == 200, response.text
        score = _score(client, project, assessment)
        assert score["started"] is True
        assert {flag["state"] for flag in _flags(score).values()} == {"not_evaluated"}


def test_once_every_requirement_is_decided_the_flags_step_aside(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags all")
        for requirement in _all_requirements(client, project):
            _requirement(client, project, assessment, requirement, "Not Met")
        score = _score(client, project, assessment)
        assert score["all_decided"] is True
        assert score["check_flags"] == {}
        assert not score["conditional"]["eligible"]


def test_hints_name_the_next_work_for_partial_credit_and_the_ssp(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags hints")
        assert _score(client, project, assessment)["hints"] == []
        _requirement(client, project, assessment, "IA.L2-3.5.3", "Not Met")
        _requirement(client, project, assessment, "SC.L2-3.13.11", "Not Met")
        _requirement(client, project, assessment, "CA.L2-3.12.4", "Not Met")
        hints = _score(client, project, assessment)["hints"]
        joined = " ".join(hints)
        assert "Record partial or no implementation for IA.L2-3.5.3 / SC.L2-3.13.11" in joined
        assert "An up-to-date SSP is needed to complete the assessment" in joined
        assert "blocker" not in joined.lower()


def test_display_flags_do_not_change_any_figure(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _setup(client, "flags figures")
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        score = _score(client, project, assessment)
        deducted = sum(line["points"] or 0 for line in score["deductions"])
        assert score["verified"]["value"] == score["score"] == 110 - deducted
