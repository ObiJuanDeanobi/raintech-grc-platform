"""The POA&M list endpoint: every POA&M item or corrective action of one project."""

import re
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_105_cmmc_scoring_findings import (
    _client,
    _objectives,
    _requirement,
    _set,
)
from api.tests.test_issue_141_verified_score import _partial
from api.tests.test_issue_m3_active_assessment_backend import create_assessment
from api.tests.test_issue_m3_remediation_validation import RECORD as HIPAA_RECORD
from api.tests.test_issue_m3_remediation_validation import make_ready, setup_case, vpath

# Weights: 3.1.1 is a 5-point requirement; 3.1.3, 3.1.7 and 3.1.8 are 1-point (Annex A).
FIVE_POINT = "AC.L2-3.1.1"
ONE_POINT = ["AC.L2-3.1.3", "AC.L2-3.1.7", "AC.L2-3.1.8"]
NEVER = "AC.L2-3.1.20"


def _list(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/poam-items")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _move(client: TestClient, project: str, action: str, state: str) -> None:
    response = client.put(
        f"/api/projects/{project}/corrective-actions/{action}",
        json={"actor_id": "johnathan", "state": state},
    )
    assert response.status_code == 200, response.text


def _item(client: TestClient, project: str, assessment: str, requirement: str, **body: Any) -> str:
    created = client.post(
        f"/api/projects/{project}/assessments/{assessment}/requirements/{requirement}/poam",
        json=body or {"draft": True},
    )
    assert created.status_code == 201, created.text
    return cast(str, created.json()["poam_items"][-1]["id"])


def test_empty_project_lists_nothing(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC empty", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        body = _list(client, project, assessment)
        assert body["variant"] == "cmmc" and body["items"] == []
        assert body["counts"]["total"] == 0
        assert body["missing_fields"] == ["owner", "due_date"]
        assert client.get(f"/api/projects/{project}/assessments/nope/poam-items").status_code == 404


def test_cmmc_listing_statuses_weights_eligibility_and_closure(tmp_path: Path) -> None:
    requirements = [FIVE_POINT, *ONE_POINT]
    with _client(tmp_path) as client:
        project = _project(client, "CMMC poam list", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for requirement in requirements:
            _requirement(client, project, assessment, requirement, "Not Met")
        ids = {
            FIVE_POINT: _item(client, project, assessment, FIVE_POINT, draft=True),
            ONE_POINT[0]: _item(client, project, assessment, ONE_POINT[0], title="Open one"),
            ONE_POINT[1]: _item(client, project, assessment, ONE_POINT[1], title="Withdrawn one"),
            ONE_POINT[2]: _item(client, project, assessment, ONE_POINT[2], title="Closed one"),
        }
        _move(client, project, ids[ONE_POINT[1]], "Withdrawn")
        _requirement(client, project, assessment, ONE_POINT[2], "Met")
        closed = client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/{ONE_POINT[2]}"
            f"/poam/{ids[ONE_POINT[2]]}/close",
            json={"rationale": "Synthetic: control restored."},
        )
        assert closed.status_code == 200, closed.text

        body = _list(client, project, assessment)
        by_requirement = {item["record_id"]: item for item in body["items"]}
        assert set(by_requirement) == set(requirements)
        # Default order: open work, then draft, then closed, then withdrawn.
        assert [item["status"] for item in body["items"]] == [
            "Open",
            "Draft",
            "Closed",
            "Withdrawn",
        ]
        assert body["counts"] == {
            "open": 2,
            "draft": 1,
            "closed": 1,
            "withdrawn": 1,
            "ready_for_validation": 0,
            "total": 4,
        }
        five = by_requirement[FIVE_POINT]
        assert five["status_label"] == "Draft" and five["weight"] == 5
        assert five["eligibility"]["state"] == "not_eligible"
        assert "only 1-point requirements" in five["eligibility"]["reason"]
        assert {"citation", "requirement_title", "work_area"} <= set(five)
        one = by_requirement[ONE_POINT[0]]
        assert one["weight"] == 1 and one["eligibility"]["state"] == "eligible"
        assert one["title"] == "Open one" and one["closure_rationale"] is None
        done = by_requirement[ONE_POINT[2]]
        assert done["closure_rationale"] == "Synthetic: control restored."
        assert done["closed_at"] and done["weight"] is None
        assert done["eligibility"]["state"] == "not_applicable"
        # Withdrawn counts as not open: its requirement is no longer planned.
        assert body["not_met_without_plan"]["requirement_ids"] == [ONE_POINT[1]]
        assert body["not_met_count"] == 3  # the Closed one is Met now
        assert len(body["work_areas"]) == 1


def test_cmmc_never_eligible_requirement_is_flagged(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC never", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, NEVER, "Not Met")
        _item(client, project, assessment, NEVER, draft=True)
        item = _list(client, project, assessment)["items"][0]
        assert item["eligibility"]["state"] == "not_eligible"
        assert "never be on a POA&M" in item["eligibility"]["reason"]


def test_items_are_scoped_to_their_project(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        mine = _project(client, "CMMC mine", CMMC_FRAMEWORK_ID)
        mine_assessment = create_assessment(client, mine)
        other = _project(client, "CMMC other", CMMC_FRAMEWORK_ID)
        other_assessment = create_assessment(client, other)
        _requirement(client, other, other_assessment, ONE_POINT[0], "Not Met")
        _item(client, other, other_assessment, ONE_POINT[0], title="Other client item")
        assert _list(client, mine, mine_assessment)["items"] == []
        assert len(_list(client, other, other_assessment)["items"]) == 1
        # An assessment id from another project is not found under this project.
        crossed = client.get(f"/api/projects/{mine}/assessments/{other_assessment}/poam-items")
        assert crossed.status_code == 404


def test_hipaa_lists_corrective_actions_without_eligibility(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, action = setup_case(client)
        body = _list(client, project, assessment)
        assert body["variant"] == "hipaa" and body["scored"] is False
        (item,) = body["items"]
        assert item["id"] == action and item["record_id"] == HIPAA_RECORD
        assert item["title"] == "Action" and item["status_label"] == "Open"
        assert item["weight"] is None
        assert item["eligibility"] == {"state": "not_applicable", "reason": ""}
        assert body["counts"]["open"] == 1 and body["counts"]["draft"] == 0
        assert body["not_met_without_plan"]["count"] == 0
        _move(client, project, action, "Ready for Validation")
        body = _list(client, project, assessment)
        assert body["counts"]["ready_for_validation"] == 1
        assert body["items"][0]["status_label"] == "Ready for validation"
        _move(client, project, action, "Withdrawn")
        body = _list(client, project, assessment)
        assert body["counts"]["open"] == 0 and body["counts"]["withdrawn"] == 1
        # A withdrawn action no longer plans the Not Met record.
        assert body["not_met_without_plan"]["requirement_ids"] == [HIPAA_RECORD]


def test_hipaa_not_needed_is_not_counted_as_missing_an_action(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, _ = setup_case(client)
        rec = f"/api/projects/{project}/assessments/{assessment}/records/{HIPAA_RECORD}"
        saved = client.put(
            f"{rec}/reconciliation", json={"outcome": "not_needed", "rationale": "Out of scope."}
        )
        assert saved.status_code == 200, saved.text
        body = _list(client, project, assessment)
        assert body["not_met_without_plan"]["count"] == 0


def _overview_open(client: TestClient, project: str, assessment: str) -> int:
    """The open count the Overview's Remediate step shows ("N POA&M items open" or
    "N corrective actions open"), wherever it sits in the figure."""
    body = client.get(f"/api/projects/{project}/assessments/{assessment}/overview").json()
    step = next(item for item in body["steps"] if item["label"] == "Remediate")
    match = re.search(r"(\d+) (?:POA&M items?|corrective actions?) open", step["figure"])
    assert match, step["figure"]
    return int(match.group(1))


def test_hipaa_action_unlinked_by_not_needed_is_still_listed_and_counted(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, action = setup_case(client)
        rec = f"/api/projects/{project}/assessments/{assessment}/records/{HIPAA_RECORD}"
        saved = client.put(
            f"{rec}/reconciliation", json={"outcome": "not_needed", "rationale": "Out of scope."}
        )
        assert saved.status_code == 200, saved.text
        body = _list(client, project, assessment)
        (item,) = body["items"]
        assert item["id"] == action and item["status"] == "Open"
        assert item["record_id"] is None and item["linked"] is False
        assert item["citation"] == "Not linked to a record"
        assert body["counts"]["open"] == 1 == _overview_open(client, project, assessment)
        # The record is marked Not needed, so it is reported as such, not as missing a plan.
        assert body["not_met_without_plan"] == {
            "count": 0,
            "requirement_ids": [],
            "not_needed_count": 1,
        }


def test_open_means_not_closed_or_withdrawn_and_matches_the_overview(tmp_path: Path) -> None:
    requirements = ["AC.L2-3.1.3", "AC.L2-3.1.5", "AC.L2-3.1.7", "AC.L2-3.1.8"]
    with _client(tmp_path) as client:
        project = _project(client, "CMMC open count", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for requirement in requirements:
            _requirement(client, project, assessment, requirement, "Not Met")
        _item(client, project, assessment, requirements[0], draft=True)
        _item(client, project, assessment, requirements[1], title="Open")
        waiting = _item(client, project, assessment, requirements[2], title="Waiting")
        withdrawn = _item(client, project, assessment, requirements[3], title="Withdrawn")
        _move(client, project, waiting, "Waiting")
        _move(client, project, withdrawn, "Withdrawn")
        body = _list(client, project, assessment)
        # Draft counts as open, as in the Overview; Withdrawn does not.
        assert body["counts"]["open"] == 3 and body["counts"]["draft"] == 1
        assert body["counts"]["open"] == _overview_open(client, project, assessment)
    with _client(tmp_path / "hipaa") as client:
        project, assessment, action = setup_case(client)
        assert _list(client, project, assessment)["counts"]["open"] == 1
        assert _overview_open(client, project, assessment) == 1
        _move(client, project, action, "Withdrawn")
        assert _list(client, project, assessment)["counts"]["open"] == 0
        assert _overview_open(client, project, assessment) == 0


def test_conditional_exception_3_13_11_weights_and_eligibility(tmp_path: Path) -> None:
    requirement = "SC.L2-3.13.11"
    with _client(tmp_path) as client:
        project = _project(client, "CMMC 3.13.11", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, requirement, "Not Met")
        _item(client, project, assessment, requirement, draft=True)
        # No implementation level recorded: full 5 points, not eligible.
        (item,) = _list(client, project, assessment)["items"]
        assert item["weight"] == 5 and item["eligibility"]["state"] == "not_eligible"
        # Encryption employed but not FIPS-validated: 3 points, the named exception.
        _partial(client, project, assessment, requirement, "partial")
        (item,) = _list(client, project, assessment)["items"]
        assert item["weight"] == 3 and item["eligibility"]["state"] == "eligible"
        assert "Named exception" in item["eligibility"]["reason"]
        _partial(client, project, assessment, requirement, "none")
        (item,) = _list(client, project, assessment)["items"]
        assert item["weight"] == 5 and item["eligibility"]["state"] == "not_eligible"


def test_evidence_pending_requirement_keeps_its_weight_and_eligibility(tmp_path: Path) -> None:
    requirement = ONE_POINT[0]
    with _client(tmp_path) as client:
        project = _project(client, "CMMC evidence pending", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, requirement, "Not Met")
        _item(client, project, assessment, requirement, title="Collect the logs")
        # Met without evidence or a documented interview: Met, but evidence pending.
        for objective in _objectives(client, project, assessment, requirement):
            _set(client, assessment, objective, "Not Met")
            saved = client.put(
                f"/api/assessments/{assessment}/determinations/{objective}",
                json={"status": "Met"},
            )
            assert saved.status_code == 200, saved.text
        (item,) = _list(client, project, assessment)["items"]
        assert item["requirement_status"] == "Met"
        assert item["weight"] == 1 and item["eligibility"]["state"] == "eligible"


def test_hipaa_item_closed_through_validation_shows_its_closure_rationale(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, action = setup_case(client)
        client.put(
            f"/api/assessments/{assessment}/determinations/{HIPAA_RECORD}",
            json={"status": "Not Met", "interview_observation": "Observed safeguard."},
        )
        make_ready(client, project, action)
        done = client.post(
            vpath(project, assessment, action),
            json={"outcome": "Validated", "notes": "Interview reviewed."},
        )
        assert done.status_code == 200, done.text
        body = _list(client, project, assessment)
        (item,) = body["items"]
        assert item["status"] == "Closed" and item["closure_rationale"] == "Interview reviewed."
        assert item["closed_at"] and item["record_id"] == HIPAA_RECORD
        assert body["counts"]["open"] == 0 and body["counts"]["closed"] == 1
