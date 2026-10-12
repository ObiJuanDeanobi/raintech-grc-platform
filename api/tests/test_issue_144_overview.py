"""The Overview dashboard endpoint (Issue #144)."""

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_105_cmmc_scoring_findings import _client, _requirement
from api.tests.test_issue_143_poam_draft import _draft
from api.tests.test_issue_m3_active_assessment_backend import create_assessment


def _close_blockers(client: TestClient, project: str, assessment: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/close-readiness")
    assert response.status_code == 200, response.text
    return cast(list[dict[str, Any]], response.json()["blockers"])


def _overview(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/overview")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_new_cmmc_project_has_four_steps_and_all_fourteen_families(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC overview", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        body = _overview(client, project, assessment)
        assert [step["label"] for step in body["steps"]] == [
            "Scope",
            "Assess",
            "Remediate",
            "Deliver",
        ]
        assert all(step["figure"] and step["target"] for step in body["steps"])
        assert len(body["families"]) == 14
        for family in body["families"]:
            assert family["decided"] == 0 and family["total"] > 0 and family["not_met"] == 0
        assert body["not_met"] == []
        assert body["resume"] is None
        assert body["left_before_issue"]["count"] > 300
        assert body["left_before_issue"]["groups"]
        assert client.get(f"/api/projects/{project}/assessments/nope/overview").status_code == 404


def test_not_met_list_shows_poam_state_and_withdrawn_counts_as_none(tmp_path: Path) -> None:
    requirements = ["AC.L2-3.1.1", "AC.L2-3.1.3", "AC.L2-3.1.5", "AC.L2-3.1.7", "AC.L2-3.1.8"]
    with _client(tmp_path) as client:
        project = _project(client, "CMMC poam states", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for requirement in requirements:
            _requirement(client, project, assessment, requirement, "Not Met")
        # [0] none; [1] draft; [2] open; [3] withdrawn; [4] closed.
        ids: dict[str, str] = {}
        for requirement in requirements[1:]:
            created = _draft(client, project, assessment, requirement)
            assert created.status_code == 201, created.text
            ids[requirement] = created.json()["poam_items"][0]["id"]

        def move(requirement: str, state: str) -> None:
            response = client.put(
                f"/api/projects/{project}/corrective-actions/{ids[requirement]}",
                json={"actor_id": "johnathan", "state": state},
            )
            assert response.status_code == 200, response.text

        move(requirements[2], "Open")
        move(requirements[3], "Withdrawn")
        # An item closes once its requirement is Met; the requirement then fails again.
        _requirement(client, project, assessment, requirements[4], "Met")
        closed = client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/{requirements[4]}"
            f"/poam/{ids[requirements[4]]}/close",
            json={"rationale": "Synthetic: control restored."},
        )
        assert closed.status_code == 200, closed.text
        _requirement(client, project, assessment, requirements[4], "Not Met")
        body = _overview(client, project, assessment)
        states = {item["record_id"]: item["poam_state"] for item in body["not_met"]}
        assert states == dict(
            zip(requirements, ["none", "draft", "open", "none", "closed"], strict=True)
        )
        assert {"citation", "title"} <= set(body["not_met"][0])
        # Closed and Withdrawn items do not plan a requirement.
        assert body["not_met_without_poam"] == {
            "count": 3,
            "requirement_ids": [requirements[0], requirements[3], requirements[4]],
        }
        assert sum(family["not_met"] for family in body["families"]) == 5


def test_resume_points_at_the_requirement_changed_last(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC resume", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        _requirement(client, project, assessment, "AC.L2-3.1.5", "Met")
        # An objective of an earlier requirement changes last: resume at its parent.
        detail = client.get(
            f"/api/projects/{project}/assessments/{assessment}/records/AC.L2-3.1.1"
        ).json()
        objective = detail["children"][0]["record_id"]
        changed = client.put(
            f"/api/assessments/{assessment}/determinations/{objective}",
            json={"status": "Not Met"},
        )
        assert changed.status_code == 200, changed.text
        body = _overview(client, project, assessment)
        assert body["resume"]["record_id"] == "AC.L2-3.1.1"
        assert body["resume"]["citation"] and body["resume"]["title"]
        assert [item["record_id"] for item in body["not_met"]] == ["AC.L2-3.1.1"]


def test_hipaa_overview_has_status_counts_per_rule_and_no_score(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        client_id = client.post("/api/clients", json={"name": "HIPAA overview"}).json()["id"]
        project = client.post(
            f"/api/clients/{client_id}/projects", json={"name": "HIPAA overview"}
        ).json()["id"]
        assessment = create_assessment(client, project)
        body = _overview(client, project, assessment)
        assert body["variant"] == "hipaa"
        assert "score" not in body and body["families"] == []
        rules = {entry["rule"]: entry for entry in body["status_counts"]}
        assert set(rules) == {"security", "privacy", "breach"}
        for entry in rules.values():
            assert entry["total"] > 0
            assert sum(entry["counts"].values()) == entry["total"]
            assert entry["counts"]["Blank"] == entry["total"]
        assert [step["label"] for step in body["steps"]] == [
            "Scope",
            "Assess",
            "Remediate",
            "Deliver",
        ]
        assert body["not_met"] == [] and body["not_met_without_poam"] is None


def test_step_figures_use_singular_and_plural_correctly(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC plurals", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        steps = {s["label"]: s["figure"] for s in _overview(client, project, assessment)["steps"]}
        assert steps["Remediate"] == "0 open POA&M items · 1 gap without a plan"
        assert steps["Assess"].endswith("objectives decided")
        _draft(client, project, assessment, "AC.L2-3.1.1")
        steps = {s["label"]: s["figure"] for s in _overview(client, project, assessment)["steps"]}
        assert steps["Remediate"] == "1 open POA&M item · 0 gaps without a plan"


def test_withdrawn_poam_item_is_not_open_on_the_overview_or_in_the_close_check(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC withdrawn", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        item = _draft(client, project, assessment, "AC.L2-3.1.1").json()["poam_items"][0]
        before = _overview(client, project, assessment)
        assert "poam_open" in {b["code"] for b in _close_blockers(client, project, assessment)}
        assert "poam_open" in {g["key"] for g in before["left_before_issue"]["groups"]}

        withdrawn = client.put(
            f"/api/projects/{project}/corrective-actions/{item['id']}",
            json={"actor_id": "johnathan", "state": "Withdrawn"},
        )
        assert withdrawn.status_code == 200, withdrawn.text
        body = _overview(client, project, assessment)
        steps = {s["label"]: s["figure"] for s in body["steps"]}
        assert steps["Remediate"] == "0 open POA&M items · 1 gap without a plan"
        assert [(n["record_id"], n["poam_state"]) for n in body["not_met"]] == [
            ("AC.L2-3.1.1", "none")
        ]
        assert "poam_open" not in {g["key"] for g in body["left_before_issue"]["groups"]}
        # The Overview and the close check must agree.
        assert "poam_open" not in {b["code"] for b in _close_blockers(client, project, assessment)}
