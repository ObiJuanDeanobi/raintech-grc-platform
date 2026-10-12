"""Drafts any time, watermarked, never stored, never issued (GitHub issue #145)."""

import io
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from api.main import create_app
from api.tests.test_issue_107_cmmc_ssp import _project as cmmc_project

BANNER = "DRAFT — NOT ISSUED"
STORED_TABLES = (
    "generated_packages",
    "generated_components",
    "source_snapshots",
    "generation_attempts",
    "issuance_snapshots",
    "package_review_events",
)


def _client(tmp_path: Path) -> tuple[TestClient, Path, Path]:
    db = tmp_path / "db.sqlite"
    files = tmp_path / "files"
    return (
        TestClient(create_app(database_path=db, storage_path=files, backup_path=files / "backups")),
        db,
        files,
    )


def _hipaa_unapproved(client: TestClient, suffix: str) -> tuple[str, str]:
    """A HIPAA project that has only been started: no Profile approval, nothing decided."""
    org = client.post("/api/clients", json={"name": f"Client {suffix}"}).json()["id"]
    project = client.post(f"/api/clients/{org}/projects", json={"name": f"HIPAA {suffix}"}).json()[
        "id"
    ]
    started = client.post(f"/api/projects/{project}/start-assessment")
    assert started.status_code == 201, started.text
    return project, started.json()["assessment"]["id"]


def _draft(
    client: TestClient, project: str, assessment: str, package: str | None = None
) -> Response:
    query = f"?package={package}" if package else ""
    return client.get(f"/api/projects/{project}/assessments/{assessment}/draft{query}")


def _zip(response: Response) -> zipfile.ZipFile:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(response.content))


def _counts(db: Path) -> dict[str, int]:
    with sqlite3.connect(db) as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in STORED_TABLES
        }


def _tree(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def _audits(db: Path) -> int:
    with sqlite3.connect(db) as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE action='package.draft_generated'"
            ).fetchone()[0]
        )


def _docx_parts(archive: zipfile.ZipFile) -> tuple[str, str, str]:
    document = archive.read("word/document.xml").decode()
    ET.fromstring(document)  # still well-formed
    return (
        document,
        archive.read("word/header_draft.xml").decode(),
        archive.read("word/_rels/document.xml.rels").decode(),
    )


def _assert_docx_is_draft(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as docx:
        document, header, rels = _docx_parts(docx)
        assert BANNER in header
        assert "header_draft.xml" in rels
        assert "/word/header_draft.xml" in docx.read("[Content_Types].xml").decode()
        sections = re.findall(r"<w:sectPr\b.*?</w:sectPr>", document, flags=re.S)
        assert sections, "a document always has at least one section"
        for section in sections:
            assert 'w:type="default" r:id="rIdDraftHeader"' in section
        assert f"{BANNER} — " in document  # title prefix
        return document


def _assert_xlsx_is_draft(data: bytes) -> int:
    with zipfile.ZipFile(io.BytesIO(data)) as workbook:
        sheets = [n for n in workbook.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
        assert len(sheets) >= 4
        for name in sheets:
            xml = workbook.read(name).decode()
            ET.fromstring(xml)
            assert "&amp;CDRAFT" in xml, name
            assert BANNER in xml, name
        return len(sheets)


def test_hipaa_draft_works_with_undecided_items_and_an_unapproved_profile(tmp_path: Path) -> None:
    client, db, files = _client(tmp_path)
    with client:
        project, assessment = _hipaa_unapproved(client, "draft")
        before_counts, before_files = _counts(db), _tree(files)
        response = _draft(client, project, assessment)
        archive = _zip(response)
        assert response.headers["content-disposition"].startswith('attachment; filename="DRAFT_')
        names = sorted(archive.namelist())
        assert names == [
            "DRAFT_RainTech_HIPAA_Combined_Assessment_Report_v2.docx",
            "DRAFT_RainTech_HIPAA_POAM_v2.xlsx",
        ]
        report = _assert_docx_is_draft(archive.read(names[0]))
        assert "Not yet decided" in report
        assert "Profile version 1 (not yet approved)" in report
        assert _assert_xlsx_is_draft(archive.read(names[1])) >= 4

        # Nothing was stored, frozen or written next to the managed files.
        assert _counts(db) == before_counts == dict.fromkeys(STORED_TABLES, 0)
        assert _tree(files) == before_files
        assert _audits(db) == 1


def test_a_draft_never_enters_an_issuance(tmp_path: Path) -> None:
    client, db, _ = _client(tmp_path)
    with client:
        project, assessment = _hipaa_unapproved(client, "never-issued")
        _zip(_draft(client, project, assessment))
        # The issue act refuses an assessment that is not ready, and a draft left nothing to issue.
        refused = client.post(
            f"/api/projects/{project}/assessments/{assessment}/issue",
            json={"actor_id": "johnathan"},
        )
        assert refused.status_code == 409
        assert client.get(f"/api/projects/{project}/packages").json() == []
    assert _counts(db)["issuance_snapshots"] == 0


def test_a_second_draft_reflects_new_data(tmp_path: Path) -> None:
    client, db, _ = _client(tmp_path)
    with client:
        project, assessment = _hipaa_unapproved(client, "fresh")
        first = _assert_docx_is_draft(
            _zip(_draft(client, project, assessment)).read(
                "DRAFT_RainTech_HIPAA_Combined_Assessment_Report_v2.docx"
            )
        )
        with sqlite3.connect(db) as connection:
            record_id = connection.execute(
                """SELECT record_id FROM framework_records
                   WHERE carries_determination = 1 AND designation = 'required'
                   ORDER BY sort_order LIMIT 1"""
            ).fetchone()[0]
        # Decide one item, then ask again.
        decided = client.put(
            f"/api/assessments/{assessment}/determinations/{record_id}",
            json={
                "status": "Not Met",
                "interview_observation": "Fresh observation for the second draft.",
            },
        )
        assert decided.status_code == 200, decided.text
        second = _assert_docx_is_draft(
            _zip(_draft(client, project, assessment)).read(
                "DRAFT_RainTech_HIPAA_Combined_Assessment_Report_v2.docx"
            )
        )
        assert first != second
        assert first.count("Not yet decided") > second.count("Not yet decided")
        assert _audits(db) == 2
        assert _counts(db)["generated_packages"] == 0


def test_hipaa_draft_after_approval_names_the_approved_profile(tmp_path: Path) -> None:
    from api.tests.test_issue_m3_hipaa_sra import _setup

    client, db, _ = _client(tmp_path)
    with client:
        project, assessment, _ = _setup(client, "approved-draft")
        archive = _zip(_draft(client, project, assessment))
        report = _assert_docx_is_draft(
            archive.read("DRAFT_RainTech_HIPAA_Combined_Assessment_Report_v2.docx")
        )
        assert "not yet approved" not in report
        assert _counts(db) == dict.fromkeys(STORED_TABLES, 0)


def test_cmmc_draft_marks_every_output_and_shows_undecided(tmp_path: Path) -> None:
    client, db, files = _client(tmp_path)
    with client:
        project, assessment = cmmc_project(client, "cmmc-draft")
        before_files = _tree(files)
        # The final self-assessment draft (the default CMMC draft is the gap assessment).
        archive = _zip(_draft(client, project, assessment, "readiness_close"))
        names = sorted(archive.namelist())
        assert names == [
            "DRAFT_CMMC_L2_Assessment_Report.docx",
            "DRAFT_CMMC_POAM_History.csv",
            "DRAFT_Evidence_Index.csv",
            "DRAFT_System_Security_Plan.docx",
        ]
        for name in names:
            assert name.startswith("DRAFT_")
        for name in ("DRAFT_CMMC_POAM_History.csv", "DRAFT_Evidence_Index.csv"):
            assert archive.read(name).decode().splitlines()[0] == BANNER
        report = _assert_docx_is_draft(archive.read("DRAFT_CMMC_L2_Assessment_Report.docx"))
        assert "Not yet decided" in report
        ssp = _assert_docx_is_draft(archive.read("DRAFT_System_Security_Plan.docx"))
        assert "NOT APPROVED" in ssp
        assert _counts(db) == dict.fromkeys(STORED_TABLES, 0)
        assert _tree(files) == before_files
        assert _audits(db) == 1


def test_cmmc_draft_with_an_unapproved_profile(tmp_path: Path) -> None:
    client, db, _ = _client(tmp_path)
    with client:
        org = client.post("/api/clients", json={"name": "CMMC unapproved"}).json()["id"]
        frameworks = client.get("/api/frameworks").json()
        cmmc = next(f for f in frameworks if "cmmc" in f["id"].lower())["id"]
        project = client.post(
            f"/api/clients/{org}/projects", json={"name": "CMMC", "framework_version_id": cmmc}
        ).json()["id"]
        started = client.post(f"/api/projects/{project}/start-assessment")
        assert started.status_code == 201, started.text
        archive = _zip(
            _draft(client, project, started.json()["assessment"]["id"], "readiness_close")
        )
        report = _assert_docx_is_draft(archive.read("DRAFT_CMMC_L2_Assessment_Report.docx"))
        assert "Not yet decided" in report
        ssp = archive.read("DRAFT_System_Security_Plan.docx")
        assert "Profile version 1" not in report  # the CMMC report does not name the Profile
        assert _assert_docx_is_draft(ssp)
        assert _counts(db) == dict.fromkeys(STORED_TABLES, 0)


def test_draft_for_another_projects_assessment_is_refused(tmp_path: Path) -> None:
    client, db, _ = _client(tmp_path)
    with client:
        _, assessment = _hipaa_unapproved(client, "one")
        other, _ = _hipaa_unapproved(client, "two")
        assert _draft(client, other, assessment).status_code == 404
    assert _audits(db) == 0


@pytest.mark.parametrize("path", ["draft"])
def test_draft_endpoint_is_read_only(tmp_path: Path, path: str) -> None:
    client, _, _ = _client(tmp_path)
    with client:
        project, assessment = _hipaa_unapproved(client, "readonly")
        assert (
            client.post(f"/api/projects/{project}/assessments/{assessment}/{path}").status_code
            == 405
        )
