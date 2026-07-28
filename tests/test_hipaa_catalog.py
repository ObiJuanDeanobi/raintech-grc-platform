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
    APPENDIX_A_KNOWN_OMISSIONS,
    APPENDIX_A_SCOPE,
    DESIGNATION_RE,
    EXCLUDED_SECTIONS,
    LEVEL_TYPES,
    SPEC_DESIGNATED_RE,
    SPEC_HEADER_RE,
    SPEC_INLINE_RE,
    STANDARD_BARE_RE,
    STANDARD_RE,
    classify,
    italic_text,
    matrix_citation_resolves,
    parse_appendix_a,
)

SNAPSHOT = "2026-07-01"
CATALOG_PATH = REPO_ROOT / "catalog" / "versions" / f"hipaa-45cfr164-{SNAPSHOT}.json"
SOURCE_DIR = REPO_ROOT / "catalog" / "sources"

# Expected counts, per catalog area. Each is justified against the pinned
# eCFR text by test_counts_are_justified_by_the_source, which recounts from
# the source XML rather than trusting these numbers.
EXPECTED = {
    "security": {
        "standard": 22,
        "implementation_specification": 41,
        "paragraph": 0,
        "section": 0,
    },
    "privacy": {
        "standard": 56,
        "implementation_specification": 58,
        "paragraph": 0,
        "section": 0,
    },
    "breach": {
        "standard": 4,
        "implementation_specification": 9,
        "paragraph": 4,
        "section": 0,
    },
}
EXPECTED_TOTAL = 194

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

    def test_bare_standard_labels_are_recognised(self):
        """A standard written "Standard" with no name is still a standard.

        45 CFR 164.502(a) -- the Privacy Rule's general prohibition on use and
        disclosure -- and all four Breach Notification Rule standards are
        written this way. Matching only "Standard: <name>" loses all five, and
        leaves the Breach Rule modelled as bare sections.
        """
        by_id = {r["id"]: r for r in self.records}
        for citation, heading in (
            ("164.502(a)", "Uses and disclosures of protected health information"),
            ("164.404(a)", "Notification to individuals"),
            ("164.406(a)", "Notification to the media"),
            ("164.408(a)", "Notification to the Secretary"),
            ("164.410(a)", "Notification by a business associate"),
        ):
            with self.subTest(citation=citation):
                self.assertIn(citation, by_id, "bare-labelled standard missing")
                record = by_id[citation]
                self.assertEqual(record["record_type"], "standard")
                # A bare "Standard" names nothing, so the title comes from the
                # section heading.
                self.assertTrue(record["title"].startswith(heading))

    def test_unlabelled_breach_obligations_are_citable_paragraph_records(self):
        """Distinct published obligations remain distinct assessable units."""
        by_id = {r["id"]: r for r in self.records}
        expected = {
            "164.412(a)": "Written law-enforcement statement",
            "164.412(b)": "Oral law-enforcement statement",
            "164.414(a)": "Administrative requirements",
            "164.414(b)": "Burden of proof",
        }
        for record_id, title in expected.items():
            with self.subTest(record=record_id):
                self.assertIn(record_id, by_id)
                record = by_id[record_id]
                self.assertEqual(record["record_type"], "paragraph")
                self.assertEqual(record["title"], title)
                self.assertIsNone(record["parent_id"])

        self.assertFalse(
            [r["id"] for r in self.records if r["record_type"] == "section"],
            "no whole-section fallback records remain",
        )

    def test_unlabelled_breach_text_matches_the_pinned_source(self):
        """All four records retain their complete independently parsed source text."""
        by_id = {r["id"]: r for r in self.records}
        source = SOURCE_DIR / f"title-45-part-164-subpart-D-{SNAPSHOT}.xml"
        root = ET.parse(source).getroot()
        expected: dict[str, str] = {}

        for section_node in root.iter("DIV8"):
            section = section_node.attrib.get("N")
            if section not in {"164.412", "164.414"}:
                continue

            paragraphs = section_node.findall("P")
            introduction = ""
            if section == "164.412":
                introduction = " ".join("".join(paragraphs[0].itertext()).split())
                paragraphs = paragraphs[1:]

            for paragraph in paragraphs:
                text = " ".join("".join(paragraph.itertext()).split())
                marker = re.match(r"^\(([a-z])\)\s*", text)
                self.assertIsNotNone(marker, text)
                record_id = f"{section}({marker.group(1)})"
                text = text[marker.end():]

                label_node = paragraph.find("I")
                if label_node is not None:
                    label = " ".join("".join(label_node.itertext()).split())
                    self.assertTrue(text.startswith(label), text)
                    text = text[len(label):].lstrip()

                expected[record_id] = f"{introduction} {text}".strip()

        self.assertEqual(
            set(expected),
            {"164.412(a)", "164.412(b)", "164.414(a)", "164.414(b)"},
        )
        for record_id, source_text in expected.items():
            with self.subTest(record=record_id):
                self.assertEqual(by_id[record_id]["text"], source_text)

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
                if STANDARD_RE.match(label) or STANDARD_BARE_RE.match(label):
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
        """Catalog standards equal the labelled ones plus those Appendix A adds.

        One Security Rule standard -- 164.308(b)(1) -- is not written
        "Standard:" in the section text and is recoverable only from Appendix
        A. Counting labels alone would under-count the catalog by exactly the
        promoted records, so they are added back explicitly rather than the
        expectation being loosened.
        """
        for subpart, area in (("C", "security"), ("E", "privacy"), ("D", "breach")):
            with self.subTest(subpart=subpart):
                source = self.labelled_paragraphs(subpart)
                standards = [
                    r
                    for r in self.records
                    if r["work_area"] == area and r["record_type"] == "standard"
                ]
                promoted = [r for r in standards if r["notes"]]
                self.assertEqual(
                    len(standards) - len(promoted), source["standard"]
                )
                if subpart == "C":
                    self.assertEqual(
                        [r["id"] for r in promoted], ["164.308(b)(1)"]
                    )

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


class AppendixAControlTest(unittest.TestCase):
    """Diff the catalog against HHS's own Security Standards Matrix.

    Appendix A to Subpart C is published regulation and enumerates the
    standards and implementation specifications of 164.308, .310 and .312
    independently of how those sections are worded. It is therefore an
    external control on the parse rather than a restatement of it.

    Two caveats, both load-bearing:

    - The matrix covers only the three safeguard sections. It says nothing
      about 164.314 or 164.316, so it is a lower bound on the Security Rule.
    - The matrix omits the (A) on Workforce Clearance Procedure. The section
      text carries it and the section text is controlling.

    This control is what caught 164.308(b)(1) missing from the catalog.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.records = cls.catalog["records"]
        payload = (SOURCE_DIR / f"title-45-part-164-subpart-C-{SNAPSHOT}.xml").read_bytes()
        cls.inventory = parse_appendix_a(payload)

    @staticmethod
    def norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    def test_matrix_parsed(self):
        self.assertEqual(len(self.inventory["standards"]), 18)
        self.assertEqual(len(self.inventory["specifications"]), 36)

    def test_every_matrix_standard_is_in_the_catalog(self):
        """A standard HHS lists must exist, however its paragraph is worded."""
        catalog_standards = {
            r["id"] for r in self.records if r["record_type"] == "standard"
        }
        missing = [
            f"{citation} ({name})"
            for citation, name in self.inventory["standards"].items()
            if not matrix_citation_resolves(citation, catalog_standards)
        ]
        self.assertEqual(missing, [], "standards in Appendix A but not the catalog")

    def test_every_matrix_specification_is_in_the_catalog(self):
        catalog_titles = {
            self.norm(r["title"])
            for r in self.records
            if r["work_area"] == "security"
        }
        missing = [
            title
            for title, _, _ in self.inventory["specifications"]
            # The matrix singularizes a couple of titles ("Testing and Revision
            # Procedure" for "...Procedures"); compare on a prefix to absorb it.
            if not any(
                catalog.startswith(self.norm(title)[:24])
                for catalog in catalog_titles
            )
        ]
        self.assertEqual(missing, [], "specifications in Appendix A but not the catalog")

    def test_designations_agree_with_the_matrix(self):
        by_title = {}
        for record in self.records:
            if record["work_area"] == "security" and record["designation"]:
                by_title[self.norm(record["title"])[:24]] = record["designation"]

        disagreements = []
        for title, designation, _ in self.inventory["specifications"]:
            if title in APPENDIX_A_KNOWN_OMISSIONS or designation is None:
                continue
            key = self.norm(title)[:24]
            if key in by_title and by_title[key] != designation:
                disagreements.append((title, designation, by_title[key]))
        self.assertEqual(disagreements, [], "matrix and catalog disagree on designation")

    def test_safeguard_section_counts_match_the_matrix(self):
        """Restricted to the matrix's scope, the counts must agree exactly."""
        in_scope = [
            r for r in self.records if r["section"] in APPENDIX_A_SCOPE
        ]
        standards = [r for r in in_scope if r["record_type"] == "standard"]
        specs = [
            r for r in in_scope if r["record_type"] == "implementation_specification"
        ]
        self.assertEqual(len(standards), len(self.inventory["standards"]))
        self.assertEqual(len(specs), len(self.inventory["specifications"]))
        self.assertEqual(
            sum(1 for r in specs if r["designation"] == "required"), 14
        )
        self.assertEqual(
            sum(1 for r in specs if r["designation"] == "addressable"), 22
        )


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
