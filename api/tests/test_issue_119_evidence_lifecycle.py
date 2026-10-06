"""Evidence replacement, recycle bin, purge guard, and review dates (Issue #119)."""

import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_m3_active_assessment_backend import create_assessment
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app
from api.tests.test_issue_m3_hipaa_review import _package

RECORD = "164.308(a)(1)(ii)(A)"


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(database_path=tmp_path / "workspace.db", storage_path=tmp_path / "files")
    )


def _project(client: TestClient, name: str) -> str:
    client_id = client.post("/api/clients", json={"name": name}).json()["id"]
    return str(client.post(f"/api/clients/{client_id}/projects", json={"name": name}).json()["id"])


def _upload(client: TestClient, project: str, name: str, body: bytes) -> str:
    response = client.post(
        f"/api/projects/{project}/evidence", files={"file": (name, body, "text/plain")}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _detail(client: TestClient, project: str, assessment: str) -> dict[str, Any]:
    return dict(
        client.get(f"/api/projects/{project}/assessments/{assessment}/records/{RECORD}").json()
    )


def test_replace_keeps_pinned_mappings_until_moved_explicitly(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Replace")
        assessment = create_assessment(client, project)
        artifact = _upload(client, project, "policy.txt", b"version one")
        mapped = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={"artifact_id": artifact, "record_id": RECORD, "rationale": "Policy."},
        )
        assert mapped.status_code == 201
        met = client.put(
            f"/api/assessments/{assessment}/determinations/{RECORD}", json={"status": "Met"}
        )
        assert met.status_code == 200

        replaced = client.post(
            f"/api/projects/{project}/evidence/{artifact}/versions",
            files={"file": ("policy.txt", b"version two", "text/plain")},
        )
        assert replaced.status_code == 201, replaced.text
        assert replaced.json()["version"]["version_number"] == 2
        evidence = _detail(client, project, assessment)["evidence"][0]
        assert (evidence["version_number"], evidence["latest_version_number"]) == (1, 2)
        assert _detail(client, project, assessment)["determination"]["status"] == "Met"
        root = tmp_path / "files"
        stored = sorted(p.read_bytes() for p in root.rglob("*policy.txt"))
        assert stored == [b"version one", b"version two"]  # v1 bytes were not overwritten

        moved = client.put(
            f"/api/projects/{project}/assessments/{assessment}"
            f"/evidence-mappings/{evidence['mapping_id']}/version"
        )
        assert moved.status_code == 200
        assert _detail(client, project, assessment)["evidence"][0]["version_number"] == 2
        again = client.put(
            f"/api/projects/{project}/assessments/{assessment}"
            f"/evidence-mappings/{evidence['mapping_id']}/version"
        )
        assert again.status_code == 409
        listed = client.get(f"/api/projects/{project}/evidence").json()
        assert listed[0]["version_number"] == 2


def test_recycle_bin_restore_and_purge_guard(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Bin")
        assessment = create_assessment(client, project)
        mapped = _upload(client, project, "mapped.txt", b"mapped")
        loose = _upload(client, project, "loose.txt", b"loose")
        client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={"artifact_id": mapped, "record_id": RECORD, "rationale": "Support."},
        )
        assert client.post(f"/api/projects/{project}/evidence/{mapped}/recycle").status_code == 409
        assert client.delete(f"/api/projects/{project}/evidence/{loose}").status_code == 409

        assert client.post(f"/api/projects/{project}/evidence/{loose}/recycle").status_code == 200
        assert [e["id"] for e in client.get(f"/api/projects/{project}/evidence").json()] == [mapped]
        assert [
            e["id"] for e in client.get(f"/api/projects/{project}/evidence?binned=true").json()
        ] == [loose]
        refused = client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={"artifact_id": loose, "record_id": RECORD, "rationale": "x"},
        )
        assert refused.status_code == 409

        assert client.post(f"/api/projects/{project}/evidence/{loose}/restore").status_code == 200
        assert client.post(f"/api/projects/{project}/evidence/{loose}/recycle").status_code == 200
        purged = client.delete(f"/api/projects/{project}/evidence/{loose}")
        assert purged.status_code == 200
        assert not any((tmp_path / "files").rglob("*loose.txt"))
        assert client.post(f"/api/projects/{project}/evidence/{loose}/restore").status_code == 409
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        # Version rows and hashes survive purging.
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM evidence_versions WHERE artifact_id = ?", (loose,)
            ).fetchone()[0]
            == 1
        )


def test_purge_refused_while_a_snapshot_cites_the_evidence(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "cited")
        artifact = _upload(client, project, "cited.txt", b"cited")
        assert (
            client.post(f"/api/projects/{project}/evidence/{artifact}/recycle").status_code == 200
        )
        _package(client, project, assessment)  # its source snapshot records project evidence
        refused = client.delete(f"/api/projects/{project}/evidence/{artifact}")
        assert refused.status_code == 409
        assert "source_snapshots" in refused.json()["detail"]
        assert any((tmp_path / "files").rglob("*cited.txt"))


def test_review_date_marks_overdue_without_changing_status(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project = _project(client, "Review")
        assessment = create_assessment(client, project)
        artifact = _upload(client, project, "review.txt", b"review")
        client.post(
            f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
            json={"artifact_id": artifact, "record_id": RECORD, "rationale": "Support."},
        )
        client.put(f"/api/assessments/{assessment}/determinations/{RECORD}", json={"status": "Met"})
        set_date = client.put(
            f"/api/projects/{project}/evidence/{artifact}/review-date",
            json={"review_date": "2020-01-01"},
        )
        assert set_date.json()["overdue"] is True
        assert client.get(f"/api/projects/{project}/evidence").json()[0]["overdue"] is True
        assert _detail(client, project, assessment)["determination"]["status"] == "Met"
        cleared = client.put(
            f"/api/projects/{project}/evidence/{artifact}/review-date", json={"review_date": None}
        )
        assert cleared.json()["overdue"] is False


def test_evidence_lifecycle_is_project_isolated(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        first, second = _project(client, "First"), _project(client, "Second")
        artifact = _upload(client, first, "own.txt", b"own")
        for method, suffix in (
            ("post", "/recycle"),
            ("post", "/restore"),
            ("delete", ""),
            ("put", "/review-date"),
        ):
            url = f"/api/projects/{second}/evidence/{artifact}{suffix}"
            kwargs = {"json": {"review_date": None}} if method == "put" else {}
            assert getattr(client, method)(url, **kwargs).status_code == 404
        replaced = client.post(
            f"/api/projects/{second}/evidence/{artifact}/versions",
            files={"file": ("own.txt", b"intruder", "text/plain")},
        )
        assert replaced.status_code == 404


def test_migration_cycle_and_downgrade_guard(tmp_path: Path) -> None:
    import pytest
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{(tmp_path / 'workspace.db').as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(tmp_path / "files"))
    command.upgrade(config, "head")
    command.downgrade(config, "0017")
    command.upgrade(config, "head")
    with _client(tmp_path) as client:
        project = _project(client, "Guard")
        artifact = _upload(client, project, "guard.txt", b"guard")
        client.post(f"/api/projects/{project}/evidence/{artifact}/recycle")
    with pytest.raises(RuntimeError, match="Binned evidence exists"):
        command.downgrade(config, "0017")
