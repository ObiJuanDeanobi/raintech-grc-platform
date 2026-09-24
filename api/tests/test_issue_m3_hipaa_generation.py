"""End-to-end contract tests for governed HIPAA package generation."""

import json
import sqlite3
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.renderers.hipaa import POAM_COLUMNS, report_values
from api.tests.test_issue_m3_hipaa_sra import _risk, _setup


def _ready(client: TestClient, db: Path, suffix: str = "generation") -> tuple[str, str]:
    project, assessment, profile = _setup(client, suffix)
    response = client.post(
        f"/api/projects/{project}/profile-readiness/transitions",
        json={
            "next_state": "Profile complete",
            "decision_note": "Ready for governed generation.",
            "reviewed_by": "Reviewer",
            "approval_evidence": "Approved Profile lifecycle event.",
        },
    )
    assert response.status_code == 201, response.text
    for item in client.get(f"/api/projects/{project}/sra").json()["scope_items"]:
        response = client.put(
            f"/api/projects/{project}/sra/scope",
            json={
                "profile_version_id": profile["id"],
                "scope_type": item["scope_type"],
                "target_key": item["target_key"],
                "included": True,
            },
        )
        assert response.status_code == 200, response.text
    response = client.post(f"/api/projects/{project}/risks", json=_risk(profile["id"], assessment))
    assert response.status_code == 201, response.text
    with sqlite3.connect(db) as connection:
        record_rows = [
            row
            for row in connection.execute(
                """SELECT record_id, designation FROM framework_records
                   WHERE framework_version_id = (
                       SELECT framework_version_id FROM projects WHERE id = ?
                   )
                     AND carries_determination = 1""",
                (project,),
            )
        ]
    for record_id, designation in record_rows:
        response = client.put(
            f"/api/assessments/{assessment}/determinations/{record_id}",
            json={
                "status": "Met",
                "interview_observation": "Synthetic test observation.",
                **(
                    {"addressable_disposition": "standard_measure"}
                    if designation == "addressable"
                    else {}
                ),
            },
        )
        assert response.status_code == 200, response.text
    assert client.get(f"/api/projects/{project}/assessments/{assessment}/close-readiness").json()[
        "ready"
    ]
    return project, assessment


def _app(tmp_path: Path) -> tuple[TestClient, Path]:
    db = tmp_path / "db.sqlite"
    return TestClient(create_app(database_path=db, storage_path=tmp_path / "files")), db


def test_generation_requires_ready_assessment(tmp_path: Path) -> None:
    client, _ = _app(tmp_path)
    with client:
        project, assessment, _ = _setup(client, "blocked-generation")
        response = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert response.status_code == 409
        assert "not ready" in response.json()["detail"]


def test_generation_promotes_two_parseable_components_from_one_snapshot(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "successful-generation")
        response = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert response.status_code == 201, response.text
        package = response.json()
        assert package["state"] == "promoted"
        assert (tmp_path / "generation-staging").is_dir()
        assert {item["kind"] for item in package["manifest"]["components"]} == {
            "assessment_report",
            "poam",
        }
        listed = client.get(f"/api/projects/{project}/packages").json()
        assert len(listed) == 1
        assert len(listed[0]["components"]) == 2
        assert len({listed[0]["manifest"]["source_snapshot_sha256"]}) == 1
        for component in listed[0]["components"]:
            download = client.get(
                f"/api/projects/{project}/packages/{package['id']}/components/{component['id']}"
            )
            assert download.status_code == 200
            if component["kind"] == "assessment_report":
                with ZipFile(BytesIO(download.content)) as archive:
                    assert b"Assessment Scope" in archive.read("word/document.xml")
            else:
                assert download.content.startswith(b"PK")
                with ZipFile(BytesIO(download.content)) as archive:
                    assert b"POA&amp;M ID" in archive.read("xl/worksheets/sheet2.xml")
        with sqlite3.connect(db) as connection:
            source = connection.execute("SELECT source_json FROM source_snapshots").fetchone()[0]
            assert "hipaa-v2" in source
            event = connection.execute(
                "SELECT action, entity_id FROM audit_events WHERE action='hipaa_package_generated'"
            ).fetchone()
            assert event == ("hipaa_package_generated", package["id"])


def test_reconciled_not_met_keeps_final_determination_in_generated_package(
    tmp_path: Path,
) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "not-met-generation")
        record_id = "164.308(a)(1)(ii)(B)"
        changed = client.put(
            f"/api/assessments/{assessment}/determinations/{record_id}",
            json={"status": "Not Met"},
        )
        assert changed.status_code == 200, changed.text
        reconciled = client.put(
            f"/api/projects/{project}/assessments/{assessment}/records/{record_id}/reconciliation",
            json={
                "outcome": "create",
                "title": "Synthetic finding",
                "action_title": "Synthetic open action",
            },
        )
        assert reconciled.status_code == 200, reconciled.text
        assert client.get(
            f"/api/projects/{project}/assessments/{assessment}/close-readiness"
        ).json()["ready"]

        generated = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert generated.status_code == 201, generated.text
        with sqlite3.connect(db) as connection:
            source = json.loads(
                connection.execute("SELECT source_json FROM source_snapshots").fetchone()[0]
            )
        row = next(item for item in source["records"] if item["record_id"] == record_id)
        assert row["status"] == "Not Met"
        assert row["title"] != "Synthetic open action"
        assert row["poam_status"] == "Open"
        assert row["finding_id"] and row["corrective_action_id"]
        values = report_values(source)
        assert values["not_met_count"] == "1"
        assert "Not Met" in values["final_determination"]
        assert values["project_name"].endswith(" Profile")
        assert values["client_name"].startswith("Synthetic Client")
        assert "Synthetic finding" in values["findings_grouped_by_source"]

        listed = client.get(f"/api/projects/{project}/packages").json()[0]
        report = next(c for c in listed["components"] if c["kind"] == "assessment_report")
        poam = next(c for c in listed["components"] if c["kind"] == "poam")
        base = f"/api/projects/{project}/packages/{listed['id']}/components"
        with ZipFile(BytesIO(client.get(f"{base}/{report['id']}").content)) as archive:
            document = archive.read("word/document.xml")
            assert b"Synthetic finding" in document
            assert values["project_name"].encode() in document
        with ZipFile(BytesIO(client.get(f"{base}/{poam['id']}").content)) as archive:
            namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            sheet = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
            header = next(r for r in sheet.iter(namespace + "row") if r.get("r") == "3")
            data = next(r for r in sheet.iter(namespace + "row") if r.get("r") == "4")
            header_values = ["".join(c.itertext()) for c in header.findall(namespace + "c")]
            data_values = ["".join(c.itertext()) for c in data.findall(namespace + "c")]
            assert header_values == list(POAM_COLUMNS)
            assert len(data_values) == 29
            assert record_id in data_values
            assert "Synthetic finding" in data_values
            assert "Open" in data_values


def test_rendered_outputs_contain_required_sections_and_exact_poam_columns(tmp_path: Path) -> None:
    from api.renderers.hipaa import render_poam, render_report

    root = Path(__file__).resolve().parents[2]
    source = {
        "snapshot_id": "snapshot-test",
        "template_version": "hipaa-v2",
        "framework": {"declarations": {"determination_record_ids": ["r-1"]}},
        "assessment": {"project_name": "Synthetic workspace"},
        "profile": {"client_name": "Synthetic client"},
        "records": [{"record_id": "r-1", "carries_determination": True, "status": "Met"}],
        "risks": [],
    }
    report = tmp_path / "report.docx"
    poam = tmp_path / "poam.xlsx"
    render_report(
        root / "docs/templates/hipaa/v2/RainTech_HIPAA_Combined_Assessment_Report_v2.docx",
        report,
        source,
    )
    render_poam(root / "docs/templates/hipaa/v2/RainTech_HIPAA_POAM_v2.xlsx", poam, source)
    with ZipFile(report) as archive:
        document = archive.read("word/document.xml").decode()
        for section in (
            "Assessment Scope",
            "Assessment Method",
            "Determine Scope",
            "Findings by Source",
            "Appendix C POA&amp;M Summary",
        ):
            assert section in document
    with ZipFile(poam) as archive:
        workbook_text = "".join(
            archive.read(name).decode()
            for name in archive.namelist()
            if name == "xl/sharedStrings.xml" or name.startswith("xl/worksheets/sheet")
        )
        assert len(POAM_COLUMNS) == 29
        assert all(column.replace("&", "&amp;") in workbook_text for column in POAM_COLUMNS)


def test_generation_is_project_isolated_and_path_safe(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        one, assessment = _ready(client, db, "project-one")
        two, _ = _ready(client, db, "project-two")
        package = client.post(f"/api/projects/{one}/assessments/{assessment}/packages").json()
        assert client.get(f"/api/projects/{two}/packages").json() == []
        component = package["manifest"]["components"][0]
        assert (
            client.get(
                f"/api/projects/{two}/packages/{package['id']}/components/{component['id']}"
            ).status_code
            == 404
        )
        with (
            sqlite3.connect(db) as connection,
            pytest.raises(sqlite3.IntegrityError, match="generated_components are immutable"),
        ):
            connection.execute(
                "UPDATE generated_components SET relative_path=? WHERE id=?",
                ("../outside", component["id"]),
            )
        assert (
            client.get(
                f"/api/projects/{one}/packages/{package['id']}/components/{component['id']}"
            ).status_code
            == 200
        )


def test_failed_attempt_is_invisible_and_retry_preserves_prior_promoted_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.generation as generation

    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "retry-generation")
        first = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert first.status_code == 201, first.text
        prior = client.get(f"/api/projects/{project}/packages").json()
        original = generation.render_poam

        def fail(*args: object, **kwargs: object) -> str:
            raise RuntimeError("forced poam failure")

        monkeypatch.setattr(generation, "render_poam", fail)
        failed = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert failed.status_code == 500
        assert client.get(f"/api/projects/{project}/packages").json() == prior
        with sqlite3.connect(db) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM generation_attempts WHERE state='failed'"
                ).fetchone()[0]
                == 1
            )
            assert connection.execute("SELECT COUNT(*) FROM generated_packages").fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE action='hipaa_package_generation_failed'"
            ).fetchone()[0] == 1
        monkeypatch.setattr(generation, "render_poam", original)
        retry = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert retry.status_code == 201, retry.text
        assert len(client.get(f"/api/projects/{project}/packages").json()) == 2


def test_forced_report_failure_does_not_publish_a_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import api.generation as generation

    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "report-failure")

        def fail(*args: object, **kwargs: object) -> str:
            raise RuntimeError("forced report failure")

        monkeypatch.setattr(generation, "render_report", fail)
        response = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert response.status_code == 500
        assert client.get(f"/api/projects/{project}/packages").json() == []
        with sqlite3.connect(db) as connection:
            assert connection.execute("SELECT COUNT(*) FROM generated_packages").fetchone()[0] == 0


def test_source_snapshot_and_package_records_persist_across_restart(tmp_path: Path) -> None:
    client, db = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "restart-generation")
        assert (
            client.post(f"/api/projects/{project}/assessments/{assessment}/packages").status_code
            == 201
        )
    with TestClient(create_app(database_path=db, storage_path=tmp_path / "files")) as restarted:
        packages = restarted.get(f"/api/projects/{project}/packages")
        assert packages.status_code == 200
        assert len(packages.json()) == 1
