import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from fastapi.testclient import TestClient

from api.database import configure_connection
from api.main import create_app
from api.tests.test_issue_62_versioned_profile import (
    create_project,
    lifecycle_payload,
    profile_payload,
)
from api.tests.test_workspace_api import migration_config


def _setup(client: TestClient, suffix: str = "sra") -> tuple[str, str, dict[str, Any]]:
    project = create_project(client, suffix)
    draft = client.get(f"/api/projects/{project}/profile").json()["versions"][0]
    saved = client.put(
        f"/api/projects/{project}/profile/versions/{draft['id']}",
        json=profile_payload(draft["content_revision"]),
    )
    assert saved.status_code == 200
    for status in ("Reviewed", "Approved"):
        response = client.post(
            f"/api/projects/{project}/profile/versions/{draft['id']}/lifecycle",
            json=lifecycle_payload(client, project, draft["id"], status),
        )
        assert response.status_code == 201
    assert (
        client.post(f"/api/projects/{project}/profile-readiness/acknowledgement").status_code == 201
    )
    assert (
        client.post(
            f"/api/projects/{project}/profile-readiness/transitions",
            json={"next_state": "Intake complete", "decision_note": "ready"},
        ).status_code
        == 201
    )
    assessment = client.post(f"/api/projects/{project}/assessments").json()["id"]
    return project, assessment, saved.json()


def _risk(profile: str, assessment: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "profile_version_id": profile,
        "assessment_id": assessment,
        "title": "Threat",
        "threat": "Threat",
        "vulnerability": "Vulnerability",
        "cia_impact": "Impact",
        "safeguards": "Safeguards",
        "corrective_action": "Action",
        "treatment": "corrective_action",
        "owner": "Owner",
        "status": "Open",
        "review_date": "2026-12-01",
        "inherent_likelihood": 1,
        "inherent_impact": 1,
        "residual_likelihood": 1,
        "residual_impact": 1,
        "acceptance_rationale": "",
        "approver": "",
        "approved_at": None,
        "reviewed_by": "Reviewer",
        "reviewed_at": "2026-09-01T00:00:00+00:00",
    }
    value.update(overrides)
    return value


def test_anchor_alteration_and_scope_inventory_reviews_and_exclusion(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project, assessment, profile = _setup(client)
        workspace = client.get(f"/api/projects/{project}/sra")
        assert workspace.status_code == 200
        assert workspace.json()["anchor"]["record_id"] == "164.308(a)(1)(ii)(A)"
        assert {item["scope_type"] for item in workspace.json()["scope_items"]} == {
            "system",
            "location",
            "vendor",
            "flow",
        }
        item = workspace.json()["scope_items"][0]
        assert (
            client.put(
                f"/api/projects/{project}/sra/scope",
                json={
                    "profile_version_id": profile["id"],
                    "scope_type": item["scope_type"],
                    "target_key": item["target_key"],
                    "included": False,
                },
            ).status_code
            == 422
        )
        saved = client.put(
            f"/api/projects/{project}/sra/scope",
            json={
                "profile_version_id": profile["id"],
                "scope_type": item["scope_type"],
                "target_key": item["target_key"],
                "included": False,
                "exclusion_rationale": "Not in boundary",
            },
        )
        assert saved.status_code == 200
        with sqlite3.connect(db) as c:
            row = c.execute(
                "SELECT declarations_json FROM framework_versions "
                "WHERE id = (SELECT framework_version_id FROM projects WHERE id = ?)",
                (project,),
            ).fetchone()
            declarations = json.loads(row[0])
            declarations["sra"]["anchor_record_id"] = "missing"
            c.execute(
                "UPDATE framework_versions SET declarations_json = ? "
                "WHERE id = (SELECT framework_version_id FROM projects WHERE id = ?)",
                (json.dumps(declarations), project),
            )
        assert client.get(f"/api/projects/{project}/sra").status_code == 409


def test_scope_and_risk_completion_is_derived_from_all_pinned_profile_targets(
    tmp_path: Path,
) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project, assessment, profile = _setup(client, "complete")
        workspace = client.get(f"/api/projects/{project}/sra").json()
        for item in workspace["scope_items"]:
            response = client.put(
                f"/api/projects/{project}/sra/scope",
                json={
                    "profile_version_id": profile["id"],
                    "scope_type": item["scope_type"],
                    "target_key": item["target_key"],
                    "included": True,
                },
            )
            assert response.status_code == 200
        risk = client.post(
            f"/api/projects/{project}/risks",
            json=_risk(profile["id"], assessment),
        )
        assert risk.status_code == 201
        complete = client.get(f"/api/projects/{project}/sra").json()
        assert complete["completion"] == {
            "complete": True,
            "percentage": 100,
            "missing": [],
        }


@pytest.mark.parametrize("band", [(1, 4), (3, 3), (2, 5), (4, 5)])
def test_risk_creation_and_approval_fields_by_band(tmp_path: Path, band: tuple[int, int]) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project, assessment, profile = _setup(client, str(band))
        payload = _risk(
            profile["id"],
            assessment,
            inherent_likelihood=band[0],
            inherent_impact=band[1],
            residual_likelihood=band[0],
            residual_impact=band[1],
            treatment="acceptance",
            acceptance_rationale="Reviewed and explicitly accepted",
        )
        response = client.post(f"/api/projects/{project}/risks", json=payload)
        if band[0] * band[1] > 9:
            assert response.status_code == 422
            payload.update(approver="Approver", approved_at="2026-09-01T00:00:00+00:00")
            response = client.post(f"/api/projects/{project}/risks", json=payload)
        assert response.status_code == 201
        assert response.json()["inherent"]["band"] in {"Low", "Moderate", "High", "Critical"}


@pytest.mark.parametrize("missing", ["acceptance_rationale", "owner", "review_date"])
def test_risk_acceptance_rejects_each_missing_required_field(tmp_path: Path, missing: str) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project, assessment, profile = _setup(client, missing)
        payload = _risk(
            profile["id"],
            assessment,
            treatment="acceptance",
            acceptance_rationale="Reviewed and explicitly accepted",
        )
        payload[missing] = "" if missing != "review_date" else None
        response = client.post(f"/api/projects/{project}/risks", json=payload)
        assert response.status_code == 422


@pytest.mark.parametrize("field", ["threat", "owner", "status", "reviewed_by"])
def test_risk_rejects_whitespace_only_required_text(tmp_path: Path, field: str) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project, assessment, profile = _setup(client, f"blank-{field}")
        payload = _risk(profile["id"], assessment)
        payload[field] = "   "
        response = client.post(f"/api/projects/{project}/risks", json=payload)
        assert response.status_code == 422


@pytest.mark.parametrize("missing", ["approver", "approved_at"])
def test_high_accepted_risk_rejects_each_missing_approval_field(
    tmp_path: Path, missing: str
) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project, assessment, profile = _setup(client, missing)
        payload = _risk(
            profile["id"],
            assessment,
            treatment="acceptance",
            acceptance_rationale="Reviewed and explicitly accepted",
            inherent_likelihood=2,
            inherent_impact=5,
            approver="Human Approver",
            approved_at="2026-09-01T00:00:00+00:00",
        )
        payload[missing] = "" if missing == "approver" else None
        response = client.post(f"/api/projects/{project}/risks", json=payload)
        assert response.status_code == 422


def test_cross_project_ids_and_direct_sql_constraints(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        p1, a1, v1 = _setup(client, "one")
        p2, a2, v2 = _setup(client, "two")
        assert client.post(f"/api/projects/{p1}/risks", json=_risk(v1["id"], a2)).status_code == 404
        assert client.post(f"/api/projects/{p1}/risks", json=_risk(v2["id"], a1)).status_code == 422
    with sqlite3.connect(db) as c:
        configure_connection(c)
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                """
                INSERT INTO risks(
                    id, project_id, profile_version_id, assessment_id, title, threat,
                    vulnerability, cia_impact, safeguards, corrective_action, treatment,
                    owner, status, review_date, inherent_likelihood, inherent_impact,
                    residual_likelihood, residual_impact, acceptance_rationale, approver,
                    approved_at, reviewed_by, reviewed_at, created_by, created_at, updated_at
                ) VALUES (
                    'x', ?, ?, ?, 't', 't', 'v', 'i', 's', '', 'corrective_action',
                    'o', 'Open', NULL, 1, 1, 1, 1, '', '', '', 'r',
                    '2026-09-01T00:00:00+00:00', 'johnathan', 'now', 'now'
                )
                """,
                (p1, p2, a1),
            )


def test_risk_evidence_links_are_project_scoped(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    client = TestClient(create_app(database_path=db, storage_path=tmp_path / "files"))
    with client:
        project_a, assessment_a, profile_a = _setup(client, "evidence-a")
        project_b, _assessment_b, _profile_b = _setup(client, "evidence-b")
        risk = client.post(
            f"/api/projects/{project_a}/risks",
            json=_risk(profile_a["id"], assessment_a),
        ).json()
        artifact_a = client.post(
            f"/api/projects/{project_a}/evidence",
            files={"file": ("risk.txt", b"sanitized risk evidence", "text/plain")},
        ).json()
        artifact_b = client.post(
            f"/api/projects/{project_b}/evidence",
            files={"file": ("other.txt", b"other evidence", "text/plain")},
        ).json()
        path = f"/api/projects/{project_a}/risks/{risk['id']}/evidence-mappings"
        mapped = client.post(
            path,
            json={
                "artifact_id": artifact_a["id"],
                "evidence_version_id": artifact_a["version"]["id"],
                "rationale": "Supports this risk decision",
            },
        )
        assert mapped.status_code == 201
        assert mapped.json()["evidence_links"][0]["name"] == "risk.txt"
        rejected = client.post(
            path,
            json={
                "artifact_id": artifact_b["id"],
                "evidence_version_id": artifact_b["version"]["id"],
                "rationale": "Cross-project guess",
            },
        )
        assert rejected.status_code == 404


def test_migration_cycle_preserves_sra_tables(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    config = migration_config(db, tmp_path / "files")
    command.upgrade(config, "head")
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")):
        pass
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE name IN ('risks', 'sra_scope_reviews', 'risk_evidence_mappings')"
            ).fetchone()[0]
            == 3
        )
        declarations = json.loads(
            c.execute("SELECT declarations_json FROM framework_versions").fetchone()[0]
        )
        assert declarations["sra"]["anchor_record_id"] == "164.308(a)(1)(ii)(A)"
        assert c.execute("SELECT COUNT(*) FROM framework_records").fetchone()[0] == 194
        assert (
            c.execute(
                "SELECT COUNT(*) FROM framework_records WHERE carries_determination = 1"
            ).fetchone()[0]
            == 149
        )
    command.downgrade(config, "0007")
    with sqlite3.connect(db) as c:
        declarations = json.loads(
            c.execute("SELECT declarations_json FROM framework_versions").fetchone()[0]
        )
        assert "sra" not in declarations
    command.upgrade(config, "head")
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE name IN ('risks', 'sra_scope_reviews', 'risk_evidence_mappings')"
            ).fetchone()[0]
            == 3
        )
        declarations = json.loads(
            c.execute("SELECT declarations_json FROM framework_versions").fetchone()[0]
        )
        assert declarations["sra"]["anchor_record_id"] == "164.308(a)(1)(ii)(A)"
        assert c.execute("SELECT COUNT(*) FROM framework_records").fetchone()[0] == 194
