"""Flow alignment, part 1 (ADR 0022): the Overview is progress only; the blank state is neutral.

Compliance-conclusion logic (docs/PROJECT_OPERATING_MODEL.md, Test Depth): nothing here
changes a score, a determination or a gate. The Overview and the score response carry
display flags and progress figures only; the close check still blocks at finalize time.
"""

import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest
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
from api.tests.test_issue_142_evidence_staleness import _map_many, _upload
from api.tests.test_issue_144_overview import _overview
from api.tests.test_issue_145_issue_act import _issue
from api.tests.test_issue_m3_active_assessment_backend import create_assessment
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app
from api.tests.test_issue_m3_substantive_reopening import _issued_with_not_met, _reopen


def _steps(body: dict[str, Any]) -> dict[str, str]:
    return {step["label"]: step["figure"] for step in body["steps"]}


def _hipaa_project(client: TestClient, name: str) -> tuple[str, str]:
    client_id = client.post("/api/clients", json={"name": name}).json()["id"]
    project = client.post(f"/api/clients/{client_id}/projects", json={"name": name}).json()["id"]
    return project, create_assessment(client, project)


def test_blank_cmmc_score_is_flagged_not_started_without_changing_the_numbers(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC blank score", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        blank = _score(client, project, assessment)
        # The display flags are new; every figure is exactly what it was.
        assert blank["started"] is False and blank["all_decided"] is False
        assert blank["verified"]["value"] == blank["score"] == -203
        assert blank["projected"]["value"] == -203
        assert blank["conditional"]["eligible"] is False

        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        begun = _score(client, project, assessment)
        assert begun["started"] is True and begun["all_decided"] is False


def test_checks_become_evaluable_only_when_every_requirement_is_decided(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC all decided", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        requirements = _all_requirements(client, project)
        for requirement in requirements[:-1]:
            _requirement(client, project, assessment, requirement, "Not Met")
        assert _score(client, project, assessment)["all_decided"] is False
        _requirement(client, project, assessment, requirements[-1], "Not Met")
        done = _score(client, project, assessment)
        assert done["started"] is True and done["all_decided"] is True
        assert done["score"] == done["verified"]["value"] < 0


def test_overview_is_progress_only_for_a_new_cmmc_project(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC progress", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        body = _overview(client, project, assessment)
        assert "left_before_issue" not in body
        steps = _steps(body)
        assert steps["Scope"] == "Profile: no facts recorded yet"
        assert steps["Assess"] == "0 of 320 decided"
        assert steps["Remediate"] == "0 gaps need a POA&M · 0 POA&M items open"
        assert steps["Deliver"] == "Draft available"
        everything = " ".join(steps.values()).lower()
        for banned in ("not approved", "left before issue", "item", "blocker", "fail"):
            assert banned not in everything.replace("poa&m items", ""), banned
        assert body["evidence_progress"] is None


def test_every_figure_carries_its_list_and_the_close_check_still_blocks(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC links", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        body = _overview(client, project, assessment)
        parts = {part["text"]: part["group"] for step in body["steps"] for part in step["parts"]}
        undecided = next(group for text, group in parts.items() if text.endswith("decided"))
        assert undecided["key"] == "undecided" and undecided["label"] == "Not decided yet"
        assert undecided["count"] > 300 and undecided["record_ids"]
        gap = parts["1 gap needs a POA&M"]
        assert gap["key"] == "gaps_no_plan" and gap["record_ids"] == ["AC.L2-3.1.3"]
        assert gap["label"] == "NOT MET without a POA&M"
        # Hard gates are unchanged: the close check keeps its groups for the finalize dialog.
        close = client.get(
            f"/api/projects/{project}/assessments/{assessment}/close-readiness"
        ).json()
        assert close["status"] == "Blocked" and close["groups"]
        assert {"undecided", "profile", "ssp"} <= {g["key"] for g in close["groups"]}


def test_met_awaiting_evidence_is_progress_with_a_list_behind_it(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC pending evidence", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project, assessment, "AC.L2-3.1.1")
        for objective in objectives:
            response = client.put(
                f"/api/assessments/{assessment}/determinations/{objective}",
                json={"status": "Met", "interview_observation": ""},
            )
            assert response.status_code == 200, response.text
        progress = _overview(client, project, assessment)["evidence_progress"]
        assert progress["text"] == f"{len(objectives)} Met awaiting evidence"
        group = progress["group"]
        assert group["key"] == "met_no_evidence"
        assert group["label"] == "Met, evidence still needed"
        assert group["record_ids"] == objectives


def _save_profile(
    client: TestClient, project: str, version: dict[str, Any], values: list[Any]
) -> Any:
    response = client.put(
        f"/api/projects/{project}/profile/versions/{version['id']}",
        json={
            "expected_revision": version["content_revision"],
            "values": [
                {
                    "section": "scope",
                    "field_key": key,
                    "label": key,
                    "value": text,
                    "source": "Synthetic interview",
                    "reviewer": "Johnathan",
                    "last_reviewed_at": "2026-10-12T00:00:00+00:00",
                }
                for key, text in values
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_profile_progress_counts_recorded_facts_without_implying_completeness(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC profile progress", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        # The neutral Profile form declares no required fields, so there is no "N of M".
        assert _steps(_overview(client, project, assessment))["Scope"] == (
            "Profile: no facts recorded yet"
        )
        draft = client.get(f"/api/projects/{project}/profile").json()["versions"][0]
        _save_profile(
            client,
            project,
            draft,
            [
                ("project_name", "CMMC profile progress"),
                ("organization_name", "Synthetic Defense LLC"),
                ("cui_flow", "Unknown"),
            ],
        )
        scope = _steps(_overview(client, project, assessment))["Scope"]
        # Two recorded facts, one recorded unknown to follow up (not counted as recorded).
        assert scope == "Profile: 2 facts recorded · 1 to follow up"
        assert " of " not in scope and "approved" not in scope


def test_profile_progress_follows_the_newest_working_version(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC profile v2", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        v1 = client.get(f"/api/projects/{project}/profile").json()["versions"][0]
        _save_profile(client, project, v1, [("organization_name", "Synthetic Defense LLC")])
        created = client.post(
            f"/api/projects/{project}/profile/versions", json={"base_version_id": v1["id"]}
        )
        assert created.status_code == 201, created.text
        v2 = created.json()
        _save_profile(
            client,
            project,
            v2,
            [("organization_name", "Synthetic Defense LLC"), ("system_name", "Enclave")],
        )
        assert _steps(_overview(client, project, assessment))["Scope"] == (
            "Profile: 2 facts recorded"
        )


def test_hipaa_overview_has_no_blocker_groups_and_names_deliver_by_draft_then_final(
    tmp_path: Path,
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "flow-final")
        before = _overview(client, project, assessment)
        assert "left_before_issue" not in before
        assert _steps(before)["Deliver"] == "Draft available"
        response = _issue(client, project, assessment, "Final.")
        assert response.status_code == 201, response.text
        after = _steps(_overview(client, project, assessment))["Deliver"]
        issued = response.json()["issued_at"]
        assert after.startswith("Final v1 · ")
        assert after.endswith(f"{int(issued[8:10])} " + _month(issued) + f" {issued[:4]}")
        assert "item" not in after


def _month(iso: str) -> str:
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return names[int(iso[5:7]) - 1]


def test_a_new_hipaa_project_overview_uses_decided_not_objectives(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _hipaa_project(client, "HIPAA progress")
        body = _overview(client, project, assessment)
        assert "left_before_issue" not in body
        steps = _steps(body)
        assert steps["Assess"].endswith("decided") and "objective" not in steps["Assess"]
        assert steps["Remediate"] == "0 corrective actions open"
        assert steps["Deliver"] == "Draft available"
        close = client.get(
            f"/api/projects/{project}/assessments/{assessment}/close-readiness"
        ).json()
        labels = {group["key"]: group["label"] for group in close["groups"]}
        assert labels["undecided"] == "Specifications not decided"


def test_evidence_coverage_lists_requirements_with_no_evidence(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC coverage", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        everything = len(_all_requirements(client, project))
        library = cast(
            dict[str, Any], client.get(f"/api/projects/{project}/evidence-library").json()
        )
        assert len(library["requirements_without_evidence"]) == everything
        first = library["requirements_without_evidence"][0]
        assert {"record_id", "citation", "title"} <= set(first)

        objectives = _objectives(client, project, assessment, "AC.L2-3.1.1")
        artifact = _upload(client, project, "policy.txt")
        _map_many(client, project, assessment, artifact, objectives[:1])
        after = client.get(f"/api/projects/{project}/evidence-library").json()
        remaining = [item["record_id"] for item in after["requirements_without_evidence"]]
        # Evidence on one objective covers its requirement.
        assert "AC.L2-3.1.1" not in remaining
        assert len(remaining) == everything - 1


def test_hipaa_coverage_counts_deciding_records(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _hipaa_project(client, "HIPAA coverage")
        library = client.get(f"/api/projects/{project}/evidence-library").json()
        listed = len(library["requirements_without_evidence"])
        counts = _overview(client, project, assessment)["status_counts"]
        assert listed == sum(entry["total"] for entry in counts) > 0


def test_the_overview_never_reads_the_close_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Progress figures come from the Overview's own data; no close check, no evidence hashing."""

    def boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the Overview must not run the close check")

    with _client(tmp_path) as client:
        project = _project(client, "CMMC no close", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        monkeypatch.setattr("api.close.fieldwork_ready", boom)
        monkeypatch.setattr("api.overview.fieldwork_ready", boom, raising=False)
        monkeypatch.setattr("api.evidence_integrity.verify_assessment_evidence", boom)
        body = _overview(client, project, assessment)
        parts = {p["text"]: p["group"] for step in body["steps"] for p in step["parts"]}
        assert parts["1 gap needs a POA&M"]["record_ids"] == ["AC.L2-3.1.3"]
        undecided = next(g for t, g in parts.items() if t.endswith("decided"))
        assert undecided["key"] == "undecided" and "AC.L2-3.1.3a" not in undecided["record_ids"]


def test_hipaa_next_work_figures_are_progress_with_lists_behind_them(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "flow-next-work")
        with sqlite3.connect(db) as connection:
            met = [
                row[0]
                for row in connection.execute(
                    "SELECT record_id FROM determinations WHERE assessment_id=? "
                    "AND status='Met' ORDER BY record_id LIMIT 2",
                    (assessment,),
                )
            ]
            connection.execute(
                "UPDATE determinations SET status='Not Met' WHERE assessment_id=? AND record_id=?",
                (assessment, met[0]),
            )
            connection.execute(
                "UPDATE determinations SET status='N/A', na_rationale='' "
                "WHERE assessment_id=? AND record_id=?",
                (assessment, met[1]),
            )
            connection.commit()
        body = _overview(client, project, assessment)
        parts = {p["text"]: p["group"] for step in body["steps"] for p in step["parts"]}
        gap = parts["1 Not Met needs a corrective action"]
        assert gap["key"] == "gaps_no_action" and gap["record_ids"] == [met[0]]
        reason = parts["1 N/A answer needs a reason"]
        assert reason["key"] == "na_reason" and reason["record_ids"] == [met[1]]
        everything = " ".join(" ".join(p) for p in [list(parts)]).lower()
        for banned in ("blocker", "left before issue", "not approved"):
            assert banned not in everything


def test_records_to_recheck_and_new_version_in_progress_after_a_reopen(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, prior_assessment, prior, _ = _issued_with_not_met(client, db, "flow-recheck")
        with sqlite3.connect(db) as connection:
            affected = connection.execute(
                "SELECT record_id FROM determinations WHERE assessment_id=? AND status='Met' "
                "LIMIT 1",
                (prior_assessment,),
            ).fetchone()[0]
        before = _steps(_overview(client, project, prior_assessment))["Deliver"]
        assert before.startswith("Final v1 · ") and "in progress" not in before
        reopened = _reopen(client, project, prior, affected=[affected])
        assert reopened.status_code == 201, reopened.text
        successor = reopened.json()["successor_assessment_id"]
        body = _overview(client, project, successor)
        parts = {p["text"]: p["group"] for step in body["steps"] for p in step["parts"]}
        recheck = parts["1 record to recheck"]
        assert recheck["key"] == "recheck" and recheck["record_ids"] == [affected]
        assert _steps(body)["Deliver"] == "Final v1 · new version in progress"


def test_cmmc_records_to_recheck_after_a_reopen(tmp_path: Path) -> None:
    from api.tests.test_issue_108_cmmc_close_issue import _client as cmmc_client
    from api.tests.test_issue_108_cmmc_close_issue import _issuable, _sign
    from api.tests.test_issue_m3_presentation_correction import _issue as issue_package

    with cmmc_client(tmp_path) as client:
        project, _assessment, package = _issuable(client, "cmmc-recheck")
        _sign(client, project, package["id"])
        assert issue_package(client, project, package["id"]).status_code == 201
        reopened = _reopen(client, project, package["id"], affected=["AC.L2-3.1.2a"])
        assert reopened.status_code == 201, reopened.text
        successor = reopened.json()["successor_assessment_id"]
        body = _overview(client, project, successor)
        parts = {p["text"]: p["group"] for step in body["steps"] for p in step["parts"]}
        assert parts["1 record to recheck"]["record_ids"] == ["AC.L2-3.1.2a"]
        assert _steps(body)["Deliver"].endswith("new version in progress")
