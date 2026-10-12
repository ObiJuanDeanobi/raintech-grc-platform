"""The Clients home endpoint: one card of figures per client project."""

import json
import sqlite3
import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from api import evidence_lifecycle
from api.framework import CMMC_FRAMEWORK_ID
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_105_cmmc_scoring_findings import _client, _requirement, _score
from api.tests.test_issue_142_evidence_staleness import _review, _upload
from api.tests.test_issue_143_poam_draft import _draft
from api.tests.test_issue_145_issue_act import _issue
from api.tests.test_issue_m3_active_assessment_backend import create_assessment
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app

TODAY = date(2026, 10, 12)
FORBIDDEN_WORDS = ("projected", "blocker", "left_before_issue", "groups")


@pytest.fixture(autouse=True)
def _today(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[date]]:
    """A mutable "today" the API reads through ``evidence_lifecycle.today``."""
    current = [TODAY]
    monkeypatch.setattr(evidence_lifecycle, "today", lambda: current[0])
    yield current


def _home(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/home")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _card(body: dict[str, Any], project: str) -> dict[str, Any]:
    return next(card for card in body["projects"] if card["project_id"] == project)


def test_empty_workspace_has_no_cards(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert _home(client)["projects"] == []


def test_cmmc_card_shows_verified_sprs_progress_and_nothing_forbidden(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC half done", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Not Met")
        draft = _draft(client, project, assessment, "AC.L2-3.1.3")
        assert draft.status_code == 201, draft.text

        card = _card(_home(client), project)
        assert card["variant"] == "cmmc"
        assert card["client_name"] == "CMMC half done client"
        assert card["framework_id"] == CMMC_FRAMEWORK_ID
        assert card["assessment_started"] is True
        # The headline is exactly the verified figure the score screen shows.
        score = _score(client, project, assessment)
        assert card["verified_sprs"]["value"] == score["verified"]["value"]
        assert card["verified_sprs"]["maximum"] == 110
        assert card["status_counts"] is None
        progress = card["progress"]
        assert progress["total"] == 320
        decided_objectives = sum(
            len(
                client.get(
                    f"/api/projects/{project}/assessments/{assessment}/records/{requirement}"
                ).json()["children"]
            )
            for requirement in ("AC.L2-3.1.1", "AC.L2-3.1.3")
        )
        assert progress["decided"] == decided_objectives
        assert progress["percent"] == round(100 * progress["decided"] / 320)
        assert card["final"] is None
        assert card["open_actions"] == 1
        text = json.dumps(card).lower()
        assert not any(word in text for word in FORBIDDEN_WORDS)


def test_new_cmmc_project_shows_no_score_until_the_first_decision(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "CMMC new", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        card = _card(_home(client), project)
        assert card["progress"] == {"decided": 0, "total": 320, "percent": 0}
        # A blank project would read -203; the home says nothing until work starts.
        assert card["verified_sprs"] is None
        assert card["final"] is None and card["open_actions"] == 0

        _requirement(client, project, assessment, "AC.L2-3.1.1", "Not Met")
        card = _card(_home(client), project)
        assert card["progress"]["decided"] > 0
        assert (
            card["verified_sprs"]["value"]
            == (_score(client, project, assessment)["verified"]["value"])
        )


def test_project_without_assessment_has_no_progress(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Not started", CMMC_FRAMEWORK_ID)
        card = _card(_home(client), project)
        assert card["assessment_started"] is False
        assert card["progress"] is None and card["verified_sprs"] is None


def test_hipaa_card_has_counts_by_status_and_no_score(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "home-hipaa")
        card = _card(_home(client), project)
        assert card["variant"] == "hipaa"
        assert card["verified_sprs"] is None
        counts = card["status_counts"]
        assert set(counts) >= {"Met", "Not Met", "Pending", "Blank"}
        assert sum(counts.values()) == card["progress"]["total"]
        decided = counts["Met"] + counts["Not Met"] + counts.get("N/A", 0)
        assert card["progress"]["decided"] == decided
        assert not any(word in json.dumps(card).lower() for word in FORBIDDEN_WORDS)
        assert card["final"] is None

        issued = _issue(client, project, assessment)
        assert issued.status_code == 201, issued.text
        final = _card(_home(client), project)["final"]
        assert final["version"] == 1
        assert final["issued_at"] == issued.json()["issued_at"]


def test_evidence_expiring_counts_within_the_lead_time_and_expired_apart(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Evidence dates", CMMC_FRAMEWORK_ID)
        create_assessment(client, project)
        soon = _upload(client, project, "soon.txt")
        later = _upload(client, project, "later.txt")
        past = _upload(client, project, "past.txt")
        _review(client, project, soon, TODAY + timedelta(days=10))
        _review(client, project, later, TODAY + timedelta(days=90))
        _review(client, project, past, TODAY - timedelta(days=1))
        card = _card(_home(client), project)
        assert (card["evidence_expiring"], card["evidence_expired"]) == (1, 1)
        assert card["evidence_lead_days"] == 30
        with sqlite3.connect(tmp_path / "workspace.db") as connection:
            connection.execute(
                "UPDATE projects SET evidence_review_lead_days = 120 WHERE id = ?", (project,)
            )
        card = _card(_home(client), project)
        assert (card["evidence_expiring"], card["evidence_expired"]) == (2, 1)


def test_most_recently_worked_project_comes_first(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        first = _project(client, "First created", CMMC_FRAMEWORK_ID)
        second = _project(client, "Second created", CMMC_FRAMEWORK_ID)
        first_assessment = create_assessment(client, first)
        create_assessment(client, second)
        assert [card["project_id"] for card in _home(client)["projects"]] == [second, first]
        time.sleep(0.01)
        _requirement(client, first, first_assessment, "AC.L2-3.1.1", "Met")
        body = _home(client)
        assert [card["project_id"] for card in body["projects"]] == [first, second]
        assert body["projects"][0]["last_worked_at"] > body["projects"][1]["last_worked_at"]


def test_twenty_projects_open_quickly_and_reading_writes_nothing(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        for number in range(20):
            project = _project(client, f"Synthetic {number}", CMMC_FRAMEWORK_ID)
            assessment = create_assessment(client, project)
            if number % 2 == 0:
                _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        started = time.perf_counter()
        body = _home(client)
        elapsed = time.perf_counter() - started
        assert len(body["projects"]) == 20
        # Aggregate reads only. The target is 300 ms; doubled here for slow CI machines.
        assert elapsed < 0.6, f"home took {elapsed * 1000:.0f} ms"
        db = tmp_path / "workspace.db"
        with sqlite3.connect(db) as connection:
            before = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        _home(client)
        with sqlite3.connect(db) as connection:
            assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == before


# --- The home's verified SPRS is the same figure as the score screen ---------------------


def _same_as_score_screen(client: TestClient, project: str, assessment: str) -> int:
    card = _card(_home(client), project)
    verified = int(_score(client, project, assessment)["verified"]["value"])
    assert card["verified_sprs"] is not None
    assert card["verified_sprs"]["value"] == verified
    return verified


def _objectives(client: TestClient, project: str, assessment: str, requirement: str) -> list[str]:
    detail = client.get(
        f"/api/projects/{project}/assessments/{assessment}/records/{requirement}"
    ).json()
    return [child["record_id"] for child in detail["children"]]


def _put(client: TestClient, assessment: str, record: str, **body: str) -> None:
    response = client.put(f"/api/assessments/{assessment}/determinations/{record}", json=body)
    assert response.status_code == 200, response.text


def test_met_without_evidence_is_evidence_pending_on_the_home_too(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Pending evidence", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        for objective in _objectives(client, project, assessment, "AC.L2-3.1.1"):
            _put(client, assessment, objective, status="Met")
        score = _score(client, project, assessment)
        assert "AC.L2-3.1.1" in score["evidence_pending"]
        _same_as_score_screen(client, project, assessment)


def test_met_by_observation_counts_as_verified(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Observed", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        assert "AC.L2-3.1.1" not in _score(client, project, assessment)["evidence_pending"]
        _same_as_score_screen(client, project, assessment)


def test_met_on_evidence_that_then_expires_drops_out_of_the_home_score(
    tmp_path: Path, _today: list[date]
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Expiring", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project, assessment, "AC.L2-3.1.1")
        for objective in objectives:
            _put(client, assessment, objective, status="Met")
        artifact = _upload(client, project, "policy.txt")
        _review(client, project, artifact, TODAY + timedelta(days=5))
        mapped = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/bulk",
            json={"artifact_id": artifact, "record_ids": objectives, "rationale": "Synthetic."},
        )
        assert mapped.status_code == 201, mapped.text
        verified_now = _same_as_score_screen(client, project, assessment)
        _today[0] = TODAY + timedelta(days=10)
        verified_later = _same_as_score_screen(client, project, assessment)
        assert verified_later < verified_now


def test_mixed_met_and_pending_objectives_do_not_verify_the_requirement(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Mixed", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        objectives = _objectives(client, project, assessment, "AC.L2-3.1.1")
        for objective in objectives[:-1]:
            _put(client, assessment, objective, status="Met", interview_observation="Observed.")
        _put(client, assessment, objectives[-1], status="Pending")
        _requirement(client, project, assessment, "AC.L2-3.1.3", "Met")
        _same_as_score_screen(client, project, assessment)


@pytest.mark.parametrize(
    ("requirement", "implementation"),
    [("IA.L2-3.5.3", "partial"), ("IA.L2-3.5.3", "none"), ("SC.L2-3.13.11", "partial")],
)
def test_partial_credit_requirements_match_the_score_screen(
    tmp_path: Path, requirement: str, implementation: str
) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Partial credit", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, requirement, "Not Met")
        before = _same_as_score_screen(client, project, assessment)
        saved = client.put(
            f"/api/projects/{project}/assessments/{assessment}/requirements/{requirement}"
            "/partial-implementation",
            json={"implementation": implementation, "rationale": "Synthetic rationale."},
        )
        assert saved.status_code == 200, saved.text
        after = _same_as_score_screen(client, project, assessment)
        assert after != before or implementation == "none"


def _score_directly(tmp_path: Path, **options: Any) -> dict[str, Any]:
    from api.cmmc import score
    from api.main import _derived_status

    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        connection.row_factory = sqlite3.Row
        assessment = connection.execute("SELECT * FROM assessments").fetchone()
        declarations = json.loads(
            connection.execute(
                "SELECT declarations_json FROM framework_versions WHERE id = ?",
                (assessment["framework_version_id"],),
            ).fetchone()[0]
        )
        return score(connection, assessment, declarations["scoring"], _derived_status, **options)


def test_cmmc_score_default_output_is_unchanged_by_the_follow_up_option(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Follow-up option", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, project)
        _requirement(client, project, assessment, "AC.L2-3.1.1", "Met")
        pending = _objectives(client, project, assessment, "AC.L2-3.1.3")[0]
        _put(client, assessment, pending, status="Pending")
        served = _score(client, project, assessment)
        default = _score_directly(tmp_path)
        explicit = _score_directly(tmp_path, include_follow_up=True)
        assert json.dumps(default, sort_keys=True) == json.dumps(explicit, sort_keys=True)
        # The served /cmmc-score adds display-only flags (ADR 0022) that are kept out of
        # cmmc.score() on purpose; everything else must match exactly.
        display_only = {"started", "all_decided", "check_flags", "hints"}
        served_scoring = {k: v for k, v in served.items() if k not in display_only}
        assert json.dumps(default, sort_keys=True) == json.dumps(served_scoring, sort_keys=True)
        assert default["follow_up"]
        lean = _score_directly(tmp_path, include_follow_up=False)
        assert lean["follow_up"] == []
        assert {**lean, "follow_up": default["follow_up"]} == default


# --- Last worked, binned evidence, missing frameworks -------------------------------------


def _order(client: TestClient) -> list[str]:
    return [card["project_id"] for card in _home(client)["projects"]]


def test_poam_edits_count_as_work(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        older = _project(client, "Older", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, older)
        _requirement(client, older, assessment, "AC.L2-3.1.3", "Not Met")
        draft = _draft(client, older, assessment, "AC.L2-3.1.3")
        item = draft.json()["poam_items"][0]["id"]
        newer = _project(client, "Newer", CMMC_FRAMEWORK_ID)
        create_assessment(client, newer)
        assert _order(client) == [newer, older]
        moved = client.put(
            f"/api/projects/{older}/corrective-actions/{item}",
            json={"actor_id": "johnathan", "state": "Open"},
        )
        assert moved.status_code == 200, moved.text
        assert _order(client) == [older, newer]


def test_mapping_evidence_and_new_versions_count_as_work(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        older = _project(client, "Older", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, older)
        artifact = _upload(client, older, "policy.txt")
        newer = _project(client, "Newer", CMMC_FRAMEWORK_ID)
        create_assessment(client, newer)
        assert _order(client) == [newer, older]
        objectives = _objectives(client, older, assessment, "AC.L2-3.1.1")
        mapped = client.post(
            f"/api/projects/{older}/assessments/{assessment}/evidence-mappings/bulk",
            json={"artifact_id": artifact, "record_ids": objectives, "rationale": "Synthetic."},
        )
        assert mapped.status_code == 201, mapped.text
        assert _order(client) == [older, newer]
        # Work on the other project, then a new version of the first one's evidence.
        _requirement(client, newer, create_assessment_id(client, newer), "AC.L2-3.1.1", "Met")
        assert _order(client) == [newer, older]
        replaced = client.post(
            f"/api/projects/{older}/evidence/{artifact}/versions",
            files={"file": ("policy-v2.txt", b"second", "text/plain")},
        )
        assert replaced.status_code == 201, replaced.text
        assert _order(client) == [older, newer]


def create_assessment_id(client: TestClient, project: str) -> str:
    return str(client.get(f"/api/projects/{project}/assessment").json()["id"])


def test_binned_evidence_does_not_count_as_work(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        older = _project(client, "Older", CMMC_FRAMEWORK_ID)
        create_assessment(client, older)
        newer = _project(client, "Newer", CMMC_FRAMEWORK_ID)
        create_assessment(client, newer)
        artifact = _upload(client, older, "scrap.txt")
        assert _order(client) == [older, newer]
        binned = client.post(f"/api/projects/{older}/evidence/{artifact}/recycle")
        assert binned.status_code == 200, binned.text
        assert _order(client) == [newer, older]


def test_project_with_a_missing_framework_still_gets_a_card(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Orphan", CMMC_FRAMEWORK_ID)
        with sqlite3.connect(tmp_path / "workspace.db") as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "UPDATE projects SET framework_version_id = 'retired-framework' WHERE id = ?",
                (project,),
            )
        card = _card(_home(client), project)
        assert card["framework_name"] == "Framework unavailable"
        assert card["variant"] == "unknown"
        assert card["progress"] is None and card["verified_sprs"] is None
        assert card["project_name"] == "Orphan"


def test_final_version_counts_every_issued_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.issuance as issuance

    monkeypatch.setattr(issuance, "DOUBLE_SUBMIT_SECONDS", 0)
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "home-final-two")
        assert _issue(client, project, assessment).status_code == 201
        assert _card(_home(client), project)["final"]["version"] == 1
        # A second issue of unchanged data is a presentation-only correction (ADR 0021): it
        # supersedes the first and is Final v2.
        again = _issue(client, project, assessment)
        assert again.status_code == 201, again.text
        assert _card(_home(client), project)["final"]["version"] == 2


def test_one_hundred_projects_with_everything_pending_or_not_met(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        projects = []
        for number in range(100):
            project = _project(client, f"Worst {number}", CMMC_FRAMEWORK_ID)
            projects.append((project, create_assessment(client, project)))
        with sqlite3.connect(tmp_path / "workspace.db") as connection:
            objectives = [
                row[0]
                for row in connection.execute(
                    "SELECT record_id FROM framework_records WHERE framework_version_id = ?"
                    " AND carries_determination = 1",
                    (CMMC_FRAMEWORK_ID,),
                )
            ]
            for index, (_, assessment) in enumerate(projects):
                status = "Not Met" if index % 2 else "Pending"
                connection.executemany(
                    "INSERT INTO determinations(assessment_id, record_id, status, updated_at)"
                    " VALUES (?, ?, ?, '2026-10-12T00:00:00+00:00')",
                    [(assessment, record, status) for record in objectives[:-1]]
                    + [(assessment, objectives[-1], "Met")],
                )
        started = time.perf_counter()
        body = _home(client)
        elapsed = time.perf_counter() - started
        assert len(body["projects"]) == 100
        assert all(card["verified_sprs"] is not None for card in body["projects"])
        assert elapsed < 0.6, f"home took {elapsed * 1000:.0f} ms"
