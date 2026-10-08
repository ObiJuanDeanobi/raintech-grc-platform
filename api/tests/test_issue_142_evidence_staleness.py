"""Evidence library, multi-objective mapping and staleness (Issue #142).

Compliance-conclusion logic (docs/PROJECT_OPERATING_MODEL.md, Test Depth):
specification AC-024 [Amendment 2026-10], "Stale or expired evidence moves an
affected verified Met to evidence pending and lowers the verified score", and
Frameworks and Assessments [Amendment 2026-10], "... without changing the
determination". AC-007: one artifact supports several requirements and each
mapping keeps its own rationale.

"Today" is injected by replacing ``api.evidence_lifecycle.today``; staleness is
computed on read, with no scheduler.
"""

import sqlite3
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from api import evidence_lifecycle, verification
from api.framework import CMMC_FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_104_cmmc_workspace import _project
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

TODAY = date(2026, 10, 8)
OBSERVED = "Synthetic: observed with the administrator."
REQUIREMENT = "AC.L2-3.1.1"  # 5 points, six objectives


@pytest.fixture
def today(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[date]]:
    """A mutable "today" the API reads through ``evidence_lifecycle.today``."""
    current = [TODAY]
    monkeypatch.setattr(evidence_lifecycle, "today", lambda: current[0])
    yield current


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _setup(client: TestClient, name: str) -> tuple[str, str, dict[str, list[str]]]:
    project = _project(client, name, CMMC_FRAMEWORK_ID)
    assessment = create_assessment(client, project)
    index = client.get(f"/api/projects/{project}/assessment").json()["record_index"]
    objectives: dict[str, list[str]] = {}
    for record in index:
        if record["record_type"] == "objective":
            objectives.setdefault(record["parent_id"], []).append(record["record_id"])
    return project, assessment, objectives


def _save(client: TestClient, assessment: str, record: str, status: str, observed: str = "") -> Any:
    response = client.put(
        f"/api/assessments/{assessment}/determinations/{record}",
        json={"status": status, "interview_observation": observed},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _upload(client: TestClient, project: str, name: str, body: bytes = b"synthetic") -> str:
    response = client.post(
        f"/api/projects/{project}/evidence", files={"file": (name, body, "text/plain")}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _review(client: TestClient, project: str, artifact: str, when: date | None) -> None:
    response = client.put(
        f"/api/projects/{project}/evidence/{artifact}/review-date",
        json={"review_date": when.isoformat() if when else None},
    )
    assert response.status_code == 200, response.text


def _map_many(
    client: TestClient, project: str, assessment: str, artifact: str, records: list[str]
) -> list[dict[str, Any]]:
    response = client.post(
        f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/bulk",
        json={"artifact_id": artifact, "record_ids": records, "rationale": "Synthetic policy."},
    )
    assert response.status_code == 201, response.text
    return cast(list[dict[str, Any]], response.json()["mappings"])


def _score(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project}/assessments/{assessment}/cmmc-score")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _states(client: TestClient, project: str) -> dict[str, Any]:
    return cast(
        dict[str, Any], client.get(f"/api/projects/{project}/assessment").json()["record_states"]
    )


def _all_verified_by_observation(
    client: TestClient, assessment: str, objectives: dict[str, list[str]], skip: str
) -> None:
    for requirement, children in objectives.items():
        if requirement != skip:
            for objective in children:
                _save(client, assessment, objective, "Met", OBSERVED)


def _determination_rows(tmp_path: Path, assessment: str) -> tuple[list[Any], list[Any]]:
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        current = connection.execute(
            "SELECT record_id, status, interview_observation, updated_at FROM determinations "
            "WHERE assessment_id = ? ORDER BY record_id",
            (assessment,),
        ).fetchall()
        history = connection.execute(
            "SELECT * FROM determination_history WHERE assessment_id = ? ORDER BY rowid",
            (assessment,),
        ).fetchall()
    return current, history


# --- review status: the one rule behind due soon and stale -------------------


def test_review_status_boundaries() -> None:
    status = evidence_lifecycle.review_status
    assert status(None, 30, TODAY) == "current"  # no review date: current
    assert status("2026-12-01", 30, TODAY) == "current"
    assert status((TODAY + timedelta(days=31)).isoformat(), 30, TODAY) == "current"
    assert status((TODAY + timedelta(days=30)).isoformat(), 30, TODAY) == "due_soon"
    assert status(TODAY.isoformat(), 30, TODAY) == "due_soon"  # due today, not yet passed
    assert status((TODAY - timedelta(days=1)).isoformat(), 30, TODAY) == "stale"
    assert status((TODAY + timedelta(days=5)).isoformat(), 0, TODAY) == "current"
    # Stale uses the same boundary as the #119 overdue flag.
    assert evidence_lifecycle.overdue((TODAY - timedelta(days=1)).isoformat(), TODAY)
    assert not evidence_lifecycle.overdue(TODAY.isoformat(), TODAY)


# --- AC-024: staleness drops verified Met to evidence pending ----------------


def test_met_bases_drop_evidence_once_review_date_passes(tmp_path: Path) -> None:
    """Unit level: the CURRENT_MAPPING predicate against injected dates."""
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Predicate")
        objective = objectives["IA.L2-3.5.9"][0]
        _save(client, assessment, objective, "Met")
        artifact = _upload(client, project, "passwords.txt")
        _map_many(client, project, assessment, artifact, [objective])
        _review(client, project, artifact, date(2026, 11, 1))
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        connection.row_factory = sqlite3.Row
        bases = verification.met_bases
        assert bases(connection, assessment, date(2026, 10, 31))[objective] == "evidence"
        assert bases(connection, assessment, date(2026, 11, 1))[objective] == "evidence"
        assert bases(connection, assessment, date(2026, 11, 2))[objective] is None
        connection.execute("UPDATE evidence_artifacts SET review_date = NULL")
        assert bases(connection, assessment, date(2099, 1, 1))[objective] == "evidence"


def test_stale_evidence_returns_verified_met_to_pending_and_lowers_verified_score(
    tmp_path: Path, today: list[date]
) -> None:
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Stale")
        _all_verified_by_observation(client, assessment, objectives, skip=REQUIREMENT)
        children = objectives[REQUIREMENT]
        for objective in children:
            _save(client, assessment, objective, "Met")  # no observation
        artifact = _upload(client, project, "access-policy.pdf")
        _map_many(client, project, assessment, artifact, children)
        _review(client, project, artifact, TODAY + timedelta(days=60))

        fresh = _score(client, project, assessment)
        assert (fresh["verified"]["value"], fresh["projected"]["value"]) == (110, 110)
        assert _states(client, project)[REQUIREMENT]["verification"] == "verified"
        before_current, before_history = _determination_rows(tmp_path, assessment)

        today[0] = TODAY + timedelta(days=61)  # review date has passed
        stale = _score(client, project, assessment)
        assert stale["verified"]["value"] == 105  # 5-point requirement leaves verified
        assert stale["projected"]["value"] == 110  # projected still counts the Met
        assert stale["evidence_pending"] == [REQUIREMENT]
        states = _states(client, project)
        assert states[REQUIREMENT]["status"] == "Met"
        assert states[REQUIREMENT]["verification"] == "evidence_pending"
        assert all(states[o]["verification"] == "evidence_pending" for o in children)
        assert states[children[0]]["evidence_review"] == "stale"
        detail = client.get(
            f"/api/projects/{project}/assessments/{assessment}/records/{children[0]}"
        ).json()
        assert detail["determination"]["status"] == "Met"
        assert detail["determination"]["verification"] == "evidence_pending"
        assert detail["evidence"][0]["review_status"] == "stale"

        # The determination record and its history are untouched (AC-024).
        assert _determination_rows(tmp_path, assessment) == (before_current, before_history)

        # Close names the stale-evidence Met as evidence pending; it is not passed.
        close = client.get(f"/api/projects/{project}/assessments/{assessment}/close-readiness")
        assert close.status_code == 200, close.text
        pending = {
            b["link"].rsplit("/", 1)[-1]
            for b in close.json()["blockers"]
            if b["code"] == "met_evidence_pending"
        }
        assert pending == set(children)


def test_observation_still_verifies_when_evidence_goes_stale(
    tmp_path: Path, today: list[date]
) -> None:
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Observed")
        objective = objectives["IA.L2-3.5.9"][0]
        _save(client, assessment, objective, "Met", OBSERVED)
        artifact = _upload(client, project, "mfa.png")
        _map_many(client, project, assessment, artifact, [objective])
        _review(client, project, artifact, TODAY - timedelta(days=1))
        assert _states(client, project)[objective]["verification"] == "verified"
        assert _states(client, project)[objective]["evidence_review"] == "stale"


def test_renewing_with_a_current_version_restores_verified(
    tmp_path: Path, today: list[date]
) -> None:
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Renew")
        children = objectives[REQUIREMENT]
        for objective in children:
            _save(client, assessment, objective, "Met")
        artifact = _upload(client, project, "access-policy.pdf", b"2025 policy")
        _map_many(client, project, assessment, artifact, children)
        _review(client, project, artifact, TODAY - timedelta(days=1))
        assert _states(client, project)[REQUIREMENT]["verification"] == "evidence_pending"
        pending = _score(client, project, assessment)["verified"]["value"]

        replaced = client.post(
            f"/api/projects/{project}/evidence/{artifact}/versions",
            files={"file": ("access-policy.pdf", b"2026 policy", "text/plain")},
            data={"review_date": "2027-10-08", "move_mappings": "true"},
        )
        assert replaced.status_code == 201, replaced.text
        body = replaced.json()
        assert body["version"]["version_number"] == 2
        assert body["review_date"] == "2027-10-08"
        assert len(body["moved_mapping_ids"]) == len(children)

        assert _states(client, project)[REQUIREMENT]["verification"] == "verified"
        assert _score(client, project, assessment)["verified"]["value"] == pending + 5
        detail = client.get(
            f"/api/projects/{project}/assessments/{assessment}/records/{children[0]}"
        ).json()
        assert detail["evidence"][0]["version_number"] == 2
        assert detail["evidence"][0]["review_status"] == "current"
        with sqlite3.connect(tmp_path / "workspace.db") as connection:
            actions = [
                row[0]
                for row in connection.execute(
                    "SELECT action FROM audit_events WHERE entity_id = ? OR action = "
                    "'evidence.mapping_version_moved' ORDER BY rowid",
                    (artifact,),
                )
            ]
        assert "evidence.replaced" in actions and "evidence.review_date_set" in actions
        assert actions.count("evidence.mapping_version_moved") == len(children)


def test_replace_without_renewal_fields_is_unchanged(tmp_path: Path, today: list[date]) -> None:
    """#119 behaviour holds: replacement alone keeps mappings and the review date."""
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Plain replace")
        objective = objectives["IA.L2-3.5.9"][0]
        _save(client, assessment, objective, "Met")
        artifact = _upload(client, project, "a.txt", b"one")
        _map_many(client, project, assessment, artifact, [objective])
        _review(client, project, artifact, TODAY - timedelta(days=3))
        replaced = client.post(
            f"/api/projects/{project}/evidence/{artifact}/versions",
            files={"file": ("a.txt", b"two", "text/plain")},
        )
        assert replaced.status_code == 201
        assert replaced.json()["moved_mapping_ids"] == []
        detail = client.get(
            f"/api/projects/{project}/assessments/{assessment}/records/{objective}"
        ).json()
        assert (
            detail["evidence"][0]["version_number"],
            detail["evidence"][0]["latest_version_number"],
        ) == (1, 2)
        assert detail["determination"]["verification"] == "evidence_pending"
        bad = client.post(
            f"/api/projects/{project}/evidence/{artifact}/versions",
            files={"file": ("a.txt", b"three", "text/plain")},
            data={"review_date": "next year"},
        )
        assert bad.status_code == 422


# --- due soon and the project lead time --------------------------------------


def test_due_soon_uses_project_lead_time_and_does_not_unverify(
    tmp_path: Path, today: list[date]
) -> None:
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Due soon")
        objective = objectives["IA.L2-3.5.9"][0]
        _save(client, assessment, objective, "Met")
        artifact = _upload(client, project, "mfa-config.txt")
        _map_many(client, project, assessment, artifact, [objective])
        _review(client, project, artifact, TODAY + timedelta(days=20))

        library = client.get(f"/api/projects/{project}/evidence-library").json()
        assert library["lead_days"] == 30 and library["today"] == TODAY.isoformat()
        entry = library["artifacts"][0]
        assert (entry["review_status"], entry["days_until_review"]) == ("due_soon", 20)
        states = _states(client, project)
        assert states[objective]["evidence_review"] == "due_soon"
        assert states["IA.L2-3.5.9"]["evidence_review"] == "due_soon"
        assert states[objective]["verification"] == "verified"  # due soon still verifies

        lead = client.put(f"/api/projects/{project}/evidence-settings", json={"lead_days": 14})
        assert lead.status_code == 200
        entry = client.get(f"/api/projects/{project}/evidence-library").json()["artifacts"][0]
        assert entry["review_status"] == "current"
        assert _states(client, project)[objective]["evidence_review"] is None
        listed = client.get(f"/api/projects/{project}/evidence").json()[0]
        assert listed["review_status"] == "current"
        assert (
            client.put(f"/api/projects/{project}/evidence-settings", json={"lead_days": -1})
        ).status_code == 422


# --- AC-007: one artifact, several objectives, own rationale each -----------


def test_bulk_mapping_is_atomic_and_each_mapping_keeps_its_rationale(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Bulk")
        children = objectives[REQUIREMENT]
        artifact = _upload(client, project, "access-policy.pdf")
        created = _map_many(client, project, assessment, artifact, children[:3])
        assert [m["record_id"] for m in created] == children[:3]
        assert {m["rationale"] for m in created} == {"Synthetic policy."}

        # Already-mapped objective refuses the whole request; nothing is half-written.
        refused = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/bulk",
            json={"artifact_id": artifact, "record_ids": children[2:], "rationale": "Again."},
        )
        assert refused.status_code == 409
        assert children[2] in refused.json()["detail"]
        # A requirement (no determination) is not a mapping target here.
        assert (
            client.post(
                f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/bulk",
                json={"artifact_id": artifact, "record_ids": [REQUIREMENT], "rationale": "x"},
            ).status_code
            == 422
        )
        library = client.get(f"/api/projects/{project}/evidence-library").json()
        used_by = library["artifacts"][0]["used_by"]
        assert [u["record_id"] for u in used_by] == children[:3]
        assert all(u["parent_id"] == REQUIREMENT for u in used_by)

        edited = client.put(
            f"/api/projects/{project}/assessments/{assessment}"
            f"/evidence-mappings/{created[1]['id']}/rationale",
            json={"rationale": "Section 4 covers device authorization."},
        )
        assert edited.status_code == 200
        rationales = {
            u["record_id"]: u["rationale"]
            for u in client.get(f"/api/projects/{project}/evidence-library").json()["artifacts"][0][
                "used_by"
            ]
        }
        assert rationales == {
            children[0]: "Synthetic policy.",
            children[1]: "Section 4 covers device authorization.",
            children[2]: "Synthetic policy.",
        }
        blank = client.put(
            f"/api/projects/{project}/assessments/{assessment}"
            f"/evidence-mappings/{created[1]['id']}/rationale",
            json={"rationale": "   "},
        )
        assert blank.status_code == 422

        # One artifact mapping can go stale for everyone at once, but unmapping one
        # leaves the others intact.
        client.delete(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/{created[0]['id']}"
        )
        remaining = client.get(f"/api/projects/{project}/evidence-library").json()["artifacts"][0]
        assert [u["record_id"] for u in remaining["used_by"]] == children[1:3]


def test_binned_evidence_cannot_be_bulk_mapped_and_projects_are_isolated(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment, objectives = _setup(client, "Binned")
        other, other_assessment, _ = _setup(client, "Other")
        artifact = _upload(client, project, "old.txt")
        assert (
            client.post(f"/api/projects/{project}/evidence/{artifact}/recycle").status_code == 200
        )
        refused = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/bulk",
            json={
                "artifact_id": artifact,
                "record_ids": objectives[REQUIREMENT][:1],
                "rationale": "x",
            },
        )
        assert refused.status_code == 409
        assert client.get(f"/api/projects/{project}/evidence-library").json()["artifacts"] == []
        foreign = client.post(
            f"/api/projects/{other}/assessments/{other_assessment}/evidence-mappings/bulk",
            json={
                "artifact_id": artifact,
                "record_ids": objectives[REQUIREMENT][:1],
                "rationale": "x",
            },
        )
        assert foreign.status_code == 404


def test_lead_time_migration_cycle_and_downgrade_guard(tmp_path: Path) -> None:
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{(tmp_path / 'workspace.db').as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(tmp_path / "files"))
    command.upgrade(config, "head")
    command.downgrade(config, "0020")
    command.upgrade(config, "head")
    with _client(tmp_path) as client:
        project, _, _ = _setup(client, "Migrate")
        assert client.get(f"/api/projects/{project}/evidence-library").json()["lead_days"] == 30
        client.put(f"/api/projects/{project}/evidence-settings", json={"lead_days": 45})
    with pytest.raises(RuntimeError, match="custom evidence lead time"):
        command.downgrade(config, "0020")
