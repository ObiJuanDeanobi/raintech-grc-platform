"""Practitioner-guidance layer tests for CMMC (#31). Standard library only."""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

import cmmc_guidance_reconcile  # noqa: E402
from cmmc_guidance import CATALOG, EXPORT, OUTPUT, _mockup_guidance, build, export  # noqa: E402

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\(\d{3}\)\s?\d{3}-\d{4}\b|\b\d{3}([-.])\d{3}\1\d{4}\b")


def _xlsx(path: Path, rows: list[list[str]]) -> None:
    def cell(column: int, row: int, text: str) -> str:
        ref = chr(65 + column) + str(row)
        return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'

    body = "".join(
        f'<row r="{r}">' + "".join(cell(c, r, v) for c, v in enumerate(row) if v) + "</row>"
        for r, row in enumerate(rows, start=1)
    )
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path, "w") as book:
        book.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets>'
            '<sheet name="Worksheet" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        book.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{ns}"><sheetData>{body}</sheetData></worksheet>',
        )


class CmmcGuidanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.layer = json.loads(OUTPUT.read_text(encoding="utf-8"))

    def test_attaches_only_by_published_id(self) -> None:
        objectives = {r["id"] for r in self.catalog["records"] if r["record_type"] == "objective"}
        requirements = {
            r["id"] for r in self.catalog["records"] if r["record_type"] == "requirement"
        }
        self.assertEqual(self.layer["unmapped_keys"], [])
        self.assertLessEqual(set(self.layer["objectives"]), objectives)
        self.assertEqual(set(self.layer["requirements"]), requirements)
        self.assertEqual(self.layer["catalog_content_sha256"], self.catalog["content_sha256"])

    def test_guidance_is_labelled_non_authoritative_and_cannot_decide(self) -> None:
        self.assertIn("Not DoD or NIST authority", self.layer["provenance"])
        self.assertNotIn("authority", self.layer)
        allowed = {"evidence_type", "evidence_examples", "assessment_considerations"}
        for fields in self.layer["objectives"].values():
            self.assertLessEqual(set(fields), allowed)
        for fields in self.layer["requirements"].values():
            self.assertLessEqual(set(fields), {"c3pao_guidance", "worksheet_level"})

    def test_blanks_are_visible_and_counts_reconcile(self) -> None:
        total = 320
        for field, missing in self.layer["blanks"].items():
            self.assertEqual(self.layer["counts"][field], total - len(missing))
            for oid in missing:
                self.assertNotIn(field, self.layer["objectives"].get(oid, {}))
        self.assertEqual(self.catalog["counts"]["objectives"], total)

    def test_rebuild_is_deterministic(self) -> None:
        layer = build(_mockup_guidance(), self.catalog)
        self.assertEqual(layer, self.layer)
        self.assertEqual(export(layer), EXPORT.read_text(encoding="utf-8"))

    def test_derived_artifacts_contain_no_contact_identifiers(self) -> None:
        for path in (OUTPUT, EXPORT):
            content = path.read_text(encoding="utf-8")
            self.assertIsNone(EMAIL.search(content), path)
            self.assertIsNone(PHONE.search(content), path)

    def test_reconcile_reads_only_objective_rows_and_reports_differences(self) -> None:
        first = next(iter(self.layer["objectives"]))
        nist, letter = re.match(r".*-(\d+\.\d+\.\d+)([a-z]+)$", first).groups()
        fields = self.layer["objectives"][first]
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "worksheet.xlsx"
            _xlsx(
                workbook,
                [
                    ["Synthetic Client LLC", "SSP scaffold row without an objective ID"],
                    [
                        "Objective",
                        "Evidence Type",
                        "Evidence Examples",
                        "Assessment Considerations",
                    ],
                    [
                        f"{nist}[{letter}]",
                        fields.get("evidence_type", ""),
                        "changed in workbook",
                        fields.get("assessment_considerations", ""),
                    ],
                ],
            )
            out = io.StringIO()
            with mock.patch.object(sys, "argv", ["reconcile", str(workbook)]), redirect_stdout(out):
                code = cmmc_guidance_reconcile.main()
        report = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn(f"DIFF {first} evidence_examples", report)
        self.assertNotIn("Synthetic Client", report)
        self.assertIn("MISSING from workbook", report)

    def test_reconcile_refuses_a_workbook_inside_the_repository(self) -> None:
        inside = REPO_ROOT / "catalog" / "worksheet.xlsx"
        with (
            mock.patch.object(sys, "argv", ["reconcile", str(inside)]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(cmmc_guidance_reconcile.main(), 2)


if __name__ == "__main__":
    unittest.main()
