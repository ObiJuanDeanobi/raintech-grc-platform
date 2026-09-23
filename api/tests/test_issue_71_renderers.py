import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from api.renderers.hipaa import (
    POAM_COLUMNS,
    REPORT_SECTIONS,
    canonical_snapshot,
    render_poam,
    render_report,
    snapshot_sha256,
    validate_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/templates/hipaa/v2/RainTech_HIPAA_Combined_Assessment_Report_v2.docx"


def _snapshot() -> dict[str, Any]:
    return {
        "snapshot_id": "src-001",
        "template_version": "hipaa-v2",
        "framework": {
            "id": "altered-framework",
            "title": "Altered HIPAA",
            "version": "test-1",
            "declaration_id": "decl-test-1",
            "declarations": {"determination_record_ids": ["r-1"]},
        },
        "assessment": {"project_name": "Synthetic workspace", "decision": "Ready"},
        "profile": {"client_name": "Synthetic client", "snapshot_id": "profile-1"},
        "records": [
            {"record_id": "parent", "carries_determination": False, "status": ""},
            {
                "record_id": "r-1",
                "carries_determination": True,
                "status": "Met",
                "citation": "ALTERED-1",
                "title": "Altered requirement",
                "text": "Altered requirement text",
                "objective": "Altered objective",
                "designation": "addressable",
            },
        ],
        "risks": [],
    }


def test_canonical_hash_is_stable_and_declaration_drives_records() -> None:
    source = _snapshot()
    canonical = canonical_snapshot(source)
    assert canonical["source_sha256"] == snapshot_sha256(source)
    assert validate_snapshot(source) == []
    source["framework"]["declarations"]["determination_record_ids"] = ["parent"]
    assert validate_snapshot(source) == ["records[0] has non-final determination"]


def test_validation_rejects_unreconciled_not_met_and_na() -> None:
    source = _snapshot()
    source["framework"]["declarations"]["determination_record_ids"] = ["r-1"]
    source["records"][1].update(status="Not Met", finding_id=None)
    assert "records[0] Not Met requires finding_id" in validate_snapshot(source)
    source["records"][1].update(status="N/A", rationale=None)
    assert "records[0] N/A requires rationale" in validate_snapshot(source)


def test_report_render_is_parseable_and_resolves_tokens(tmp_path: Path) -> None:
    output = tmp_path / "report.docx"
    render_report(TEMPLATE, output, _snapshot())
    with ZipFile(output) as package:
        document = package.read("word/document.xml").decode("utf-8")
    assert "{{client_name}}" not in document
    assert "Synthetic client" in document
    assert "decl-test-1" in document
    assert "Altered requirement" in document
    assert "Altered requirement text" in document
    assert "{{requirement_text}}" not in document
    with ZipFile(output) as package:
        unresolved = {
            name: package.read(name).decode("utf-8", errors="ignore")
            for name in package.namelist()
            if name.startswith("word/")
            and name.endswith(".xml")
            and "{{" in package.read(name).decode("utf-8", errors="ignore")
        }
    assert unresolved == {}


def test_template_contract_is_explicit() -> None:
    assert REPORT_SECTIONS[:3] == ("Assessment Scope", "Assessment Method", "Determine Scope")
    assert "Requirement" in POAM_COLUMNS
    assert "Control Group" in POAM_COLUMNS
    assert "Control Description" in POAM_COLUMNS
    assert "Package / Snapshot ID" in POAM_COLUMNS


def test_poam_render_is_parseable_and_populates_exact_row(tmp_path: Path) -> None:
    source = _snapshot()
    source["records"][1].update(status="Not Met", finding_id="finding-1", action_id="action-1")
    output = tmp_path / "poam.xlsx"
    render_poam(ROOT / "docs/templates/hipaa/v2/RainTech_HIPAA_POAM_v2.xlsx", output, source)
    with ZipFile(output) as package:
        workbook = package.read("xl/worksheets/sheet2.xml").decode("utf-8")
        unresolved = {
            name: package.read(name).decode("utf-8", errors="ignore")
            for name in package.namelist()
            if name.startswith("xl/")
            and name.endswith(".xml")
            and "{{" in package.read(name).decode("utf-8", errors="ignore")
        }
    assert "finding-1" in workbook
    assert "action-1" in workbook
    assert "decl-test-1" not in workbook
    assert 'r="AC3"' in workbook
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    sheet = ET.fromstring(workbook)
    data_row = next(row for row in sheet.iter(namespace + "row") if row.get("r") == "4")
    assert len(data_row.findall(namespace + "c")) == 29
    assert unresolved == {}
