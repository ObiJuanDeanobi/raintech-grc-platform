"""One-click POA&M draft from a NOT MET requirement, and the unplanned count (Issue #143)."""

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_105_cmmc_scoring_findings import (
    _client,
    _finding,
    _objectives,
    _requirement,
    _score,
    _set,
)
from api.tests.test_issue_141_verified_score import _map
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

REQUIREMENT = "AC.L2-3.1.1"


def _base(project: str, assessment: str, requirement: str = REQUIREMENT) -> str:
    return f"/api/projects/{project}/assessments/{assessment}/requirements/{requirement}"


def _draft(
    client: TestClient, project: str, assessment: str, requirement: str = REQUIREMENT
) -> Any:
    return client.post(f"{_base(project, assessment, requirement)}/poam", json={"draft": True})


def _unplanned(client: TestClient, project: str) -> dict[str, Any]:
    workspace = client.get(f"/api/projects/{project}/assessment").json()
    return cast(dict[str, Any], workspace["not_met_without_poam"])


def _rows(tmp_path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        connection.row_factory = sqlite3.Row
        return list(connection.execute(sql, params))


def test_one_click_draft_is_prefilled_from_the_finding_and_never_duplicated(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC POA&M draft", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        first, second, *_ = _objectives(client, project, assessment, REQUIREMENT)
        _set(client, assessment, first, "Not Met")
        _set(client, assessment, second, "Not Met")
        note = client.put(
            f"/api/assessments/{assessment}/records/{first}/note",
            json={"note": "Examine: Synthetic: the user list is two years old."},
        )
        assert note.status_code == 200, note.text
        _map(client, project, assessment, first)

        created = _draft(client, project, assessment)
        assert created.status_code == 201, created.text
        items = created.json()["poam_items"]
        assert len(items) == 1
        item = items[0]
        assert item["status"] == "Draft"
        assert item["title"] == "AC.L2-3.1.1 Authorized Access Control [CUI Data]"
        description = item["description"]
        citations = [
            o["citation"]
            for o in _finding(client, project, assessment, REQUIREMENT)["failed_objectives"]
        ]
        assert len(citations) == 2
        for citation in citations:
            assert citation in description
        assert "Synthetic: the user list is two years old." in description
        assert f"Evidence: {first}.txt (Synthetic.)" in description

        # A repeated click is refused and names the existing item; nothing is duplicated.
        again = _draft(client, project, assessment)
        assert again.status_code == 409
        assert "AC.L2-3.1.1 Authorized Access Control [CUI Data]" in again.json()["detail"]
        assert len(_finding(client, project, assessment, REQUIREMENT)["poam_items"]) == 1

        # Creation is audited.
        audit = _rows(
            tmp_path,
            "SELECT details_json FROM audit_events WHERE action = ? AND entity_id = ?",
            ("cmmc.poam_item_created", item["id"]),
        )
        assert len(audit) == 1
        details = json.loads(audit[0]["details_json"])
        assert details["status"] == "Draft"
        assert details["prefilled_from_finding"] is True
        assert details["record_id"] == REQUIREMENT

        # The draft opens for editing inline; edits are audited.
        edit = client.put(
            f"{_base(project, assessment)}/poam/{item['id']}",
            json={"title": "Rebuild the authorized user list", "description": "Quarterly."},
        )
        assert edit.status_code == 200, edit.text
        edited = edit.json()["poam_items"][0]
        assert (edited["title"], edited["description"], edited["status"]) == (
            "Rebuild the authorized user list",
            "Quarterly.",
            "Draft",
        )
        assert (
            client.put(
                f"{_base(project, assessment)}/poam/{item['id']}", json={"title": " "}
            ).status_code
            == 422
        )
        assert _rows(
            tmp_path,
            "SELECT 1 FROM audit_events WHERE action = 'cmmc.poam_item_edited' AND entity_id = ?",
            (item["id"],),
        )

        # The manual path still works and still starts Open.
        manual = client.post(f"{_base(project, assessment)}/poam", json={"title": "Manual item"})
        assert manual.status_code == 201
        assert [i["status"] for i in manual.json()["poam_items"]] == ["Draft", "Open"]


def test_no_poam_item_is_created_automatically_and_pending_cannot_create_one(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC no automatic POA&M", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for requirement in ("AC.L2-3.1.1", "AC.L2-3.1.3", "CA.L2-3.12.4"):
            _requirement(client, project, assessment, requirement, "Not Met")
        # Determination changes open findings but never POA&M items.
        assert _finding(client, project, assessment, "AC.L2-3.1.1") is not None
        assert _rows(tmp_path, "SELECT id FROM corrective_actions") == []
        assert _unplanned(client, project)["count"] == 3

        # Pending (AC-005) and Met cannot create a POA&M draft.
        _requirement(client, project, assessment, "AC.L2-3.1.2", "Pending")
        assert _draft(client, project, assessment, "AC.L2-3.1.2").status_code == 409
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Pending")
        assert _draft(client, project, assessment, "AC.L2-3.1.3").status_code == 409
        _requirement(client, project, assessment, "AC.L2-3.1.4", "Met")
        assert _draft(client, project, assessment, "AC.L2-3.1.4").status_code == 409
        assert _rows(tmp_path, "SELECT id FROM corrective_actions") == []


def test_unplanned_not_met_count_ignores_closed_and_withdrawn_items(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC unplanned count", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        assert _unplanned(client, project) == {"count": 0, "requirement_ids": []}
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        expected = {"count": 2, "requirement_ids": ["AC.L2-3.1.1", "AC.L2-3.1.3"]}
        assert _unplanned(client, project) == expected
        # The score carries the same figure for the Overview.
        assert _score(client, project, assessment)["not_met_without_poam"] == expected

        draft = _draft(client, project, assessment).json()["poam_items"][0]
        expected = {"count": 1, "requirement_ids": ["AC.L2-3.1.3"]}
        assert _unplanned(client, project) == expected
        assert _score(client, project, assessment)["not_met_without_poam"] == expected
        assert (
            client.get(f"/api/projects/{project}/assessment").json()["record_states"][
                "AC.L2-3.1.1"
            ]["open_poam_count"]
            == 1
        )

        # A Withdrawn item does not plan the requirement; a fresh draft may be made.
        withdrawn = client.put(
            f"/api/projects/{project}/corrective-actions/{draft['id']}",
            json={"actor_id": "johnathan", "state": "Withdrawn"},
        )
        assert withdrawn.status_code == 200, withdrawn.text
        assert _unplanned(client, project)["requirement_ids"] == ["AC.L2-3.1.1", "AC.L2-3.1.3"]
        assert (
            client.put(
                f"{_base(project, assessment)}/poam/{draft['id']}", json={"title": "x"}
            ).status_code
            == 409
        )
        redraft = _draft(client, project, assessment)
        assert redraft.status_code == 201, redraft.text
        replacement = next(i for i in redraft.json()["poam_items"] if i["status"] == "Draft")
        assert _unplanned(client, project)["requirement_ids"] == ["AC.L2-3.1.3"]

        # A Closed item does not plan a requirement that later fails again.
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        closed = client.post(
            f"{_base(project, assessment)}/poam/{replacement['id']}/close",
            json={"rationale": "Synthetic: list rebuilt and reviewed."},
        )
        assert closed.status_code == 200, closed.text
        assert _unplanned(client, project)["requirement_ids"] == ["AC.L2-3.1.3"]
        _set(
            client, assessment, _objectives(client, project, assessment, REQUIREMENT)[0], "Not Met"
        )
        assert _unplanned(client, project)["requirement_ids"] == ["AC.L2-3.1.1", "AC.L2-3.1.3"]


def test_unplanned_count_is_isolated_per_project_and_absent_for_hipaa(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        first = _project(client, "CMMC first", CMMC_FRAMEWORK_ID)
        second = _project(client, "CMMC second", CMMC_FRAMEWORK_ID)
        first_assessment = create_assessment(client, first)
        second_assessment = create_assessment(client, second)
        for project, assessment in ((first, first_assessment), (second, second_assessment)):
            _requirement(client, project, assessment, REQUIREMENT, "Not Met")
        assert _draft(client, first, first_assessment).status_code == 201
        assert _unplanned(client, first)["count"] == 0
        assert _unplanned(client, second) == {"count": 1, "requirement_ids": [REQUIREMENT]}
        # Another project's item is not reachable through this project's route.
        item = _finding(client, first, first_assessment, REQUIREMENT)["poam_items"][0]
        assert (
            client.put(
                f"{_base(second, second_assessment)}/poam/{item['id']}", json={"title": "x"}
            ).status_code
            == 404
        )
        # A project's draft is refused only by its own open item.
        assert _draft(client, second, second_assessment).status_code == 201

        hipaa = _project(client, "HIPAA", FRAMEWORK_ID)
        create_assessment(client, hipaa)
        assert (
            client.get(f"/api/projects/{hipaa}/assessment").json()["not_met_without_poam"] is None
        )


def test_never_poam_requirement_draft_is_allowed_and_score_carries_the_warning(
    tmp_path: Path,
) -> None:
    """Warn, do not block: 32 CFR 170.21 eligibility comes from the score lines (#141)."""
    with _client(tmp_path) as client:
        project = _project(client, "CMMC never-POA&M", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "CA.L2-3.12.4", "Not Met")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        assert _draft(client, project, assessment, "CA.L2-3.12.4").status_code == 201
        assert _draft(client, project, assessment, "AC.L2-3.1.3").status_code == 201
        lines = {
            line["record_id"]: line for line in _score(client, project, assessment)["deductions"]
        }
        assert lines["CA.L2-3.12.4"]["conditional_poam_allowed"] is False
        assert "May never be on a POA&M" in lines["CA.L2-3.12.4"]["poam_reason"]
        assert lines["AC.L2-3.1.3"]["conditional_poam_allowed"] is True
