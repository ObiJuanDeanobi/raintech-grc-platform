from __future__ import annotations

import csv
import io
import zipfile

from cmmc_tracker.db import STATUSES, connect, init_db
from cmmc_tracker.services import (
    attach_evidence,
    completion_csv,
    delete_evidence,
    export_zip,
    replace_evidence,
    store_upload,
)


def setup_tracker(monkeypatch, tmp_path):
    monkeypatch.setenv("CMMC_TRACKER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CMMC_TRACKER_DB", str(tmp_path / "tracker.db"))
    init_db()


def test_seed_counts(monkeypatch, tmp_path):
    setup_tracker(monkeypatch, tmp_path)
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0] == 14
        assert conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0] == 110
        assert conn.execute("SELECT COUNT(*) FROM objectives").fetchone()[0] == 320
        requirement = conn.execute(
            "SELECT potential_methods, discussion, further_discussion FROM requirements WHERE id = 'AC.L2-3.1.1'"
        ).fetchone()
        assert "POTENTIAL ASSESSMENT METHODS AND OBJECTS" in requirement["potential_methods"]
        assert "DISCUSSION" in requirement["discussion"]
        assert "FURTHER DISCUSSION" in requirement["further_discussion"]
    assert "Escalating" in STATUSES


def test_evidence_reuse_and_zip_export(monkeypatch, tmp_path):
    setup_tracker(monkeypatch, tmp_path)

    evidence_id = store_upload(
        io.BytesIO(b"system security plan"),
        "SSP.pdf",
        "SSP",
        "Policy repository",
        "Reusable SSP evidence",
    )
    duplicate_id = store_upload(
        io.BytesIO(b"system security plan"),
        "SSP Copy.pdf",
        "SSP Copy",
        "",
        "",
    )
    assert duplicate_id == evidence_id

    attach_evidence("AC.L2-3.1.1a", evidence_id)
    attach_evidence("AC.L2-3.1.1b", evidence_id)
    with connect() as conn:
        assert conn.execute(
            "SELECT status FROM objective_status WHERE objective_id = 'AC.L2-3.1.1a'"
        ).fetchone()[0] == "Captured"

    path = export_zip()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert "manifest.csv" in names
        assert "1 - Access Control/AC.L2-3.1.1a-SSP.pdf" in names
        assert "1 - Access Control/AC.L2-3.1.1b-SSP.pdf" in names
        manifest_rows = list(csv.DictReader(io.StringIO(archive.read("manifest.csv").decode())))

    assert len(manifest_rows) == 2
    assert {row["Objective ID"] for row in manifest_rows} == {"AC.L2-3.1.1a", "AC.L2-3.1.1b"}


def test_replace_evidence_preserves_mappings_and_delete_removes_them(monkeypatch, tmp_path):
    setup_tracker(monkeypatch, tmp_path)
    evidence_id = store_upload(io.BytesIO(b"old ssp"), "SSP.pdf", "SSP")
    attach_evidence("AC.L2-3.1.1a", evidence_id)
    attach_evidence("AC.L2-3.1.1b", evidence_id)

    replacement_id = replace_evidence(
        evidence_id,
        io.BytesIO(b"new ssp"),
        "SSP updated.pdf",
    )

    assert replacement_id == evidence_id
    with connect() as conn:
        mappings = conn.execute(
            "SELECT objective_id FROM objective_evidence WHERE evidence_id = ? ORDER BY objective_id",
            (evidence_id,),
        ).fetchall()
        evidence = conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
    assert [row["objective_id"] for row in mappings] == ["AC.L2-3.1.1a", "AC.L2-3.1.1b"]
    assert evidence["original_filename"] == "SSP updated.pdf"
    assert evidence["title"] == "SSP"

    path = export_zip()
    with zipfile.ZipFile(path) as archive:
        assert archive.read("1 - Access Control/AC.L2-3.1.1a-SSP.pdf") == b"new ssp"

    assert delete_evidence(evidence_id) is True
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM objective_evidence").fetchone()[0] == 0
        statuses = conn.execute(
            """
            SELECT status
            FROM objective_status
            WHERE objective_id IN ('AC.L2-3.1.1a', 'AC.L2-3.1.1b')
            ORDER BY objective_id
            """
        ).fetchall()
    assert [row["status"] for row in statuses] == ["Not Captured", "Not Captured"]


def test_completion_report_has_all_objectives(monkeypatch, tmp_path):
    setup_tracker(monkeypatch, tmp_path)
    rows = list(csv.reader(io.StringIO(completion_csv())))

    assert rows[0][:4] == ["Domain", "Requirement ID", "Requirement Name", "Objective ID"]
    assert len(rows) == 321


def test_objective_detail_has_adjacent_navigation(monkeypatch, tmp_path):
    setup_tracker(monkeypatch, tmp_path)
    with connect() as conn:
        ordered_ids = [
            row["id"]
            for row in conn.execute(
                """
                SELECT o.id
                FROM objectives o
                JOIN requirements r ON r.id = o.requirement_id
                JOIN domains d ON d.code = r.domain_code
                ORDER BY d.sort_order, r.id, o.letter
                """
            ).fetchall()
        ]

    assert ordered_ids[0] == "AC.L2-3.1.1a"
    assert ordered_ids[1] == "AC.L2-3.1.1b"
    middle_index = ordered_ids.index("AC.L2-3.1.1b")
    assert ordered_ids[middle_index - 1] == "AC.L2-3.1.1a"
    assert ordered_ids[middle_index + 1] == "AC.L2-3.1.1c"
