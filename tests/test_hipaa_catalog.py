"""Structure and count tests for the pinned HIPAA catalog.

These run against the committed catalog fixture and the committed source
XML. They make no network calls, so CI verifies the catalog without
depending on eCFR availability.

Test depth follows `docs/PROJECT_OPERATING_MODEL.md`: the catalog decides
what is assessed and what is cited, so it gets real tests. The counts
asserted here are derived from the pinned source and justified in
``test_counts_are_justified_by_the_source`` rather than copied from a
summary table.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from hipaa_ingest import (  # noqa: E402
    DESIGNATION_RE,
    EXCLUDED_SECTIONS,
    LEVEL_TYPES,
    SPEC_DESIGNATED_RE,
    SPEC_HEADER_RE,
    SPEC_INLINE_RE,
    STANDARD_RE,
    classify,
    italic_text,
)

SNAPSHOT = "2026-07-01"
CATALOG_PATH = REPO_ROOT / "catalog" / "versions" / f"hipaa-45cfr164-{SNAPSHOT}.json"
SOURCE_DIR = REPO_ROOT / "catalog" / "sources"

# Expected counts, per catalog area. Each is justified against the pinned
# eCFR text by test_counts_are_justified_by_the_source, which recounts from
# the source XML rather than trusting these numbers.
EXPECTED = {
    "security": {"standard": 21, "implementation_specification": 41, "section": 0},
    "privacy": {"standard": 55, "implementation_specification": 58, "section": 0},
    "breach": {"standard": 0, "implementation_specification": 9, "section": 6},
}
EXPECTED_TOTAL = 190

# The Required/Addressable distinction exists only in the Security Rule,
# per 45 CFR 164.306(d).
EXPECTED_SECURITY_REQUIRED = 19
EXPECTED_SECURITY_ADDRESSABLE = 22


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


class CatalogStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.records = cls.catalog["records"]

    def test_catalog_covers_three_catalog_areas(self):
        """Three catalog areas, not four. The SRA is a work area."""
        areas = {area["id"] for area in self.catalog["catalog_areas"]}
        self.assertEqual(areas, {"security", "privacy", "breach"})
        self.assertEqual({r["work_area"] for r in self.records}, areas)

    def test_risk_analysis_appears_exactly_once(self):
        """The SRA must not be ingested a second time as its own area.

        Risk analysis is one Required implementation specification inside
        the Security Management Process standard.
        """
        matches = [
            r for r in self.records if r["title"].strip().lower() == "risk analysis"
        ]
        self.assertEqual(len(matches), 1, [m["citation"] for m in matches])
        record = matches[0]
        self.assertEqual(record["citation"], "45 CFR 164.308(a)(1)(ii)(A)")
        self.assertEqual(record["work_area"], "security")
        self.assertEqual(record["record_type"], "implementation_specification")
        self.assertEqual(record["designation"], "required")
        self.assertEqual(record["parent_id"], "164.308(a)(1)(i)")

    def test_record_counts_per_catalog_area(self):
        for area, expected in EXPECTED.items():
            with self.subTest(area=area):
                rows = [r for r in self.records if r["work_area"] == area]
                actual = {
                    kind: sum(1 for r in rows if r["record_type"] == kind)
                    for kind in expected
                }
                self.assertEqual(actual, expected)
        self.assertEqual(len(self.records), EXPECTED_TOTAL)

    def test_identifiers_are_unique_and_traceable(self):
        ids = [r["id"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)), "duplicate record identifiers")
        for record in self.records:
            with self.subTest(record=record["id"]):
                self.assertEqual(record["citation"], f"45 CFR {record['id']}")
                self.assertTrue(record["citation"].startswith("45 CFR 164."))
                self.assertEqual(
                    record["id"], record["section"] + record["paragraph"]
                )

    def test_parent_links_resolve_and_are_well_formed(self):
        ids = {r["id"] for r in self.records}
        by_id = {r["id"]: r for r in self.records}
        for record in self.records:
            parent = record["parent_id"]
            if parent is None:
                continue
            with self.subTest(record=record["id"]):
                self.assertIn(parent, ids, "dangling parent")
                self.assertNotEqual(parent, record["id"], "self-parent")
                self.assertTrue(
                    record["id"].startswith(by_id[parent]["section"]),
                    "parent in a different section",
                )
                self.assertIn(
                    by_id[parent]["record_type"],
                    ("standard", "section"),
                    "implementation specifications hang off a standard or section",
                )

    def test_standards_have_no_parent(self):
        for record in self.records:
            if record["record_type"] == "standard":
                self.assertIsNone(record["parent_id"], record["id"])

    def test_every_record_carries_provenance(self):
        for record in self.records:
            with self.subTest(record=record["id"]):
                self.assertTrue(record["source"].startswith("eCFR Title 45 Part 164"))
                self.assertIn(SNAPSHOT, record["source"])
                self.assertRegex(record["retrieved"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(record["title"].strip())
                self.assertTrue(record["text"].strip())

    def test_paragraph_paths_follow_cfr_level_typing(self):
        """(a)(1)(i)(A) -- a roman numeral must never sit at the top level."""
        for record in self.records:
            tokens = re.findall(r"\(([0-9A-Za-z]+)\)", record["paragraph"])
            for depth, token in enumerate(tokens):
                if depth >= len(LEVEL_TYPES):
                    continue
                with self.subTest(record=record["id"], depth=depth):
                    self.assertIn(LEVEL_TYPES[depth], classify(token))


class DesignationTest(unittest.TestCase):
    """Required/Addressable is a property of the pinned version, Subpart C only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.records = cls.catalog["records"]

    def test_version_declares_addressable_scope(self):
        version = self.catalog["framework_version"]
        self.assertTrue(version["uses_addressable"])
        self.assertIn("Subpart C", version["addressable_scope"])
        self.assertEqual(version["snapshot_date"], SNAPSHOT)

    def test_designation_only_in_the_security_rule(self):
        offenders = [
            r["citation"]
            for r in self.records
            if r["designation"] and r["subpart"] != "C"
        ]
        self.assertEqual(offenders, [], "designation outside Subpart C")

    def test_privacy_and_breach_carry_no_designation(self):
        for area in ("privacy", "breach"):
            with self.subTest(area=area):
                self.assertEqual(
                    [
                        r["citation"]
                        for r in self.records
                        if r["work_area"] == area and r["designation"]
                    ],
                    [],
                )

    def test_security_designation_counts(self):
        rows = [r for r in self.records if r["work_area"] == "security"]
        required = [r for r in rows if r["designation"] == "required"]
        addressable = [r for r in rows if r["designation"] == "addressable"]
        self.assertEqual(len(required), EXPECTED_SECURITY_REQUIRED)
        self.assertEqual(len(addressable), EXPECTED_SECURITY_ADDRESSABLE)
        # Every Security Rule implementation specification is designated.
        specs = [
            r for r in rows if r["record_type"] == "implementation_specification"
        ]
        self.assertEqual(len(required) + len(addressable), len(specs))

    def test_designation_values_are_constrained(self):
        for record in self.records:
            self.assertIn(record["designation"], (None, "required", "addressable"))


class SourceReconciliationTest(unittest.TestCase):
    """Recount from the pinned source so the expected counts are earned.

    This is what stops a parser regression from silently dropping records and
    then passing because the expected count was updated to match.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.records = cls.catalog["records"]

    @staticmethod
    def labelled_paragraphs(subpart: str):
        """Every paragraph the regulation labels, outside excluded sections."""
        path = SOURCE_DIR / f"title-45-part-164-subpart-{subpart}-{SNAPSHOT}.xml"
        root = ET.fromstring(path.read_bytes())
        found = {"standard": 0, "spec_header": 0, "spec_record": 0}
        for section_div in root.iter("DIV8"):
            if section_div.attrib.get("TYPE") != "SECTION":
                continue
            if section_div.attrib.get("N", "") in EXCLUDED_SECTIONS:
                continue
            for paragraph in section_div.iter("P"):
                label = italic_text(paragraph)
                if label is None:
                    continue
                if STANDARD_RE.match(label):
                    found["standard"] += 1
                elif SPEC_DESIGNATED_RE.match(label):
                    found["spec_record"] += 1
                elif SPEC_HEADER_RE.match(label):
                    found["spec_header"] += 1
                elif SPEC_INLINE_RE.match(label):
                    found["spec_record"] += 1
        return found

    def test_source_files_are_pinned_and_present(self):
        for subpart in ("C", "D", "E"):
            path = SOURCE_DIR / f"title-45-part-164-subpart-{subpart}-{SNAPSHOT}.xml"
            self.assertTrue(path.exists(), f"missing pinned source for subpart {subpart}")

    def test_standard_counts_match_the_source(self):
        for subpart, area in (("C", "security"), ("E", "privacy"), ("D", "breach")):
            with self.subTest(subpart=subpart):
                source = self.labelled_paragraphs(subpart)
                catalog = sum(
                    1
                    for r in self.records
                    if r["work_area"] == area and r["record_type"] == "standard"
                )
                self.assertEqual(catalog, source["standard"])

    def test_every_designated_paragraph_became_a_record(self):
        """All 41 Subpart C designations must survive ingestion.

        Three label forms carry designations, and matching only one of them
        silently drops the rest.
        """
        path = SOURCE_DIR / f"title-45-part-164-subpart-C-{SNAPSHOT}.xml"
        root = ET.fromstring(path.read_bytes())
        source_designations = 0
        for section_div in root.iter("DIV8"):
            if section_div.attrib.get("TYPE") != "SECTION":
                continue
            if section_div.attrib.get("N", "") in EXCLUDED_SECTIONS:
                continue
            for paragraph in section_div.iter("P"):
                label = italic_text(paragraph)
                if label and DESIGNATION_RE.search(label):
                    source_designations += 1

        catalog_designations = sum(
            1 for r in self.records if r["work_area"] == "security" and r["designation"]
        )
        self.assertEqual(catalog_designations, source_designations)
        self.assertEqual(
            source_designations,
            EXPECTED_SECURITY_REQUIRED + EXPECTED_SECURITY_ADDRESSABLE,
        )

    def test_appendix_a_is_not_ingested(self):
        """The Security Standards Matrix restates the rule; ingesting it doubles every record."""
        reasons = [e["unit"] for e in self.catalog["exclusions"]]
        self.assertIn("Appendix A to Subpart C of Part 164", reasons)
        self.assertLessEqual(
            sum(1 for r in self.records if r["work_area"] == "security"),
            EXPECTED["security"]["standard"]
            + EXPECTED["security"]["implementation_specification"],
        )

    def test_exclusions_are_recorded_with_reasons(self):
        self.assertTrue(self.catalog["exclusions"])
        for exclusion in self.catalog["exclusions"]:
            with self.subTest(unit=exclusion["unit"]):
                self.assertTrue(exclusion["reason"].strip())
        excluded_sections = {
            e["unit"].replace("45 CFR ", "")
            for e in self.catalog["exclusions"]
            if e["kind"] == "section"
        }
        # Nothing excluded may also appear as a record.
        for record in self.records:
            self.assertNotIn(record["section"], excluded_sections)


class ContentConstraintTest(unittest.TestCase):
    """ADR 0011: generated output makes no certification or frequency claims."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.records = cls.catalog["records"]

    def test_no_certification_claims(self):
        banned = re.compile(
            r"\b(certifies|certified|certification|compliant with HIPAA|"
            r"HIPAA[- ]certified|guarantees compliance)\b",
            re.IGNORECASE,
        )
        for record in self.records:
            with self.subTest(record=record["id"]):
                self.assertIsNone(
                    banned.search(record["title"]),
                    f"certification language in title: {record['title']}",
                )

    def test_no_invented_review_frequency(self):
        """The catalog must not assert a cadence the rule does not mandate.

        Record text is verbatim regulation, so any cadence in it is the
        rule's own. This guards the fields we author: titles and notes.
        """
        cadence = re.compile(
            r"\b(annual|annually|quarterly|monthly|every \d+ (days|months|years))\b",
            re.IGNORECASE,
        )
        for record in self.records:
            with self.subTest(record=record["id"]):
                self.assertIsNone(cadence.search(record["title"]))
                for note in record["notes"]:
                    self.assertIsNone(cadence.search(note))


if __name__ == "__main__":
    unittest.main(verbosity=2)
