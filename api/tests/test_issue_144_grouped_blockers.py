"""Close blockers counted by plain-English group (Issue #144)."""

import re
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.close import _groups
from api.framework import CMMC_FRAMEWORK_ID
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_105_cmmc_scoring_findings import _client, _requirement
from api.tests.test_issue_m3_active_assessment_backend import create_assessment


def _close(client: TestClient, project: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/close-readiness/fieldwork_ready_for_generation")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _assert_groups_match(
    body: dict[str, Any], expected: dict[str, int]
) -> dict[str, dict[str, Any]]:
    """Counts are hard-coded for a known state, not recomputed with the code under test."""
    groups = {group["key"]: group for group in body["groups"]}
    assert len(groups) == len(body["groups"])
    assert {key: group["count"] for key, group in groups.items()} == expected
    assert sum(expected.values()) == len(body["blockers"])
    for group in body["groups"]:
        assert group["label"] and group["target"]
    return groups


def test_new_cmmc_project_groups_sum_to_the_flat_list(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC new", CMMC_FRAMEWORK_ID)
        create_assessment(client, project)
        body = _close(client, project)
        groups = _assert_groups_match(body, {"profile": 2, "undecided": 320, "ssp": 1})
        flat = [b for b in body["blockers"] if b["code"] == "determination_not_final"]
        undecided = groups["undecided"]
        assert undecided["label"] == "Objectives not decided"
        assert undecided["count"] == len(flat) > 300
        assert undecided["record_ids"] == [b["link"].rsplit("/", 1)[1] for b in flat]
        assert groups["profile"]["label"] == "Profile not approved"
        assert groups["ssp"]["label"] == "SSP not approved"
        assert body["blockers"], "the flat list stays for the debug link"


def test_half_done_cmmc_project_groups_each_kind(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC half", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        body = _close(client, project)
        groups = _assert_groups_match(
            body, {"profile": 2, "undecided": 309, "not_met": 5, "ssp": 1}
        )
        # CMMC's internal close wants every objective Met, so a Not Met objective
        # is still "not decided to final"; the decided Met ones are not listed.
        record_ids = groups["undecided"]["record_ids"]
        assert not any(re.fullmatch(r"AC\.L2-3\.1\.1[a-z]", record) for record in record_ids)
        assert not any(re.fullmatch(r"AC\.L2-3\.1\.3[a-z]", record) for record in record_ids)
        # Not Met objectives are decided; they are counted on their own, not as undecided.
        assert groups["not_met"]["label"] == "Objectives still Not Met"
        assert all(re.fullmatch(r"AC\.L2-3\.1\.3[a-z]", r) for r in groups["not_met"]["record_ids"])
        assert groups["not_met"]["count"] == len(groups["not_met"]["record_ids"]) > 0
        assert "gaps_no_plan" not in groups


def test_hipaa_project_groups_sum_to_the_flat_list(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        client_id = client.post("/api/clients", json={"name": "HIPAA grouped"}).json()["id"]
        project = client.post(
            f"/api/clients/{client_id}/projects", json={"name": "HIPAA grouped"}
        ).json()["id"]
        create_assessment(client, project)
        body = _close(client, project)
        groups = _assert_groups_match(body, {"profile": 2, "undecided": 149, "sra": 2})
        assert "undecided" in groups
        assert groups["sra"]["label"] == "Security Risk Analysis incomplete"


def test_unknown_codes_go_to_other_and_counts_still_sum() -> None:
    blockers = [
        {"code": "determination_not_final", "detail": "a", "check": "x", "link": "/p/records/R1"},
        {"code": "brand_new_check", "detail": "b", "check": "x"},
        {"code": "brand_new_check", "detail": "c", "check": "x", "link": "/p/records/R2/other"},
    ]
    groups = {group["key"]: group for group in _groups(blockers)}
    assert groups["other"]["count"] == 2
    assert groups["other"]["label"] == "Other items"
    assert groups["other"]["record_ids"] == ["R2"]
    assert sum(group["count"] for group in groups.values()) == len(blockers)


def test_na_without_a_reason_is_not_counted_as_undecided() -> None:
    blockers = [
        {"code": "na_rationale_missing", "detail": "a", "check": "x", "link": "/p/records/R1"},
        {"code": "determination_not_final", "detail": "b", "check": "x", "link": "/p/records/R2"},
    ]
    groups = {group["key"]: group for group in _groups(blockers)}
    assert groups["na_reason"]["label"] == "N/A answers missing a reason"
    assert groups["na_reason"]["record_ids"] == ["R1"]
    assert groups["undecided"]["record_ids"] == ["R2"]
