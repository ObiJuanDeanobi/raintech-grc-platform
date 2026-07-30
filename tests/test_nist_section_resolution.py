"""Corpus-wide checks on 800-66r2 section resolution.

These run across all 22 Security Rule standards rather than one, because the
defect they exist to catch was invisible from a single standard. The approved
164.308(a)(1) volume sample passed a full practitioner review while seven
sibling standards were returning that standard's prompts verbatim and seven
more were returning nothing. 164.308(a)(1) was the only standard the code
resolved correctly, so no amount of scrutiny of the sample could have exposed
it.

Unlike the rest of the suite these tests need PyMuPDF and the pinned PDF, so
they skip when it is absent. A skip that goes unnoticed in CI would recreate
the same blind spot, so the dedicated CI step sets RAINTECH_REQUIRE_NIST=1 and
that turns the skip into a failure.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from hipaa_prompts import (  # noqa: E402
    CATALOG,
    NIST_PDF,
    extract_nist_prompts,
    nist_headings,
    nist_section_bounds,
    resolve_nist_citation,
)

REQUIRE = os.environ.get("RAINTECH_REQUIRE_NIST") == "1"

# The corrected extraction, pinned so a future regression has to change a
# number rather than pass quietly. 443 across 22 standards.
EXPECTED_RAW_COUNTS = {
    "164.308(a)(1)(i)": 40,
    "164.308(a)(2)": 5,
    "164.308(a)(3)(i)": 16,
    "164.308(a)(4)(i)": 21,
    "164.308(a)(5)(i)": 34,
    "164.308(a)(6)(i)": 20,
    "164.308(a)(7)(i)": 30,
    "164.308(a)(8)": 26,
    "164.308(b)(1)": 11,
    "164.310(a)(1)": 32,
    "164.310(b)": 22,
    "164.310(c)": 15,
    "164.310(d)(1)": 19,
    "164.312(a)(1)": 39,
    "164.312(b)": 21,
    "164.312(c)(1)": 22,
    "164.312(d)": 18,
    "164.312(e)(1)": 21,
    "164.314(a)(1)": 9,
    "164.314(b)(1)": 6,
    "164.316(a)": 3,
    "164.316(b)(1)": 13,
}


def security_standards() -> list[str]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return [
        record["id"]
        for record in catalog["records"]
        if record["work_area"] == "security" and record["record_type"] == "standard"
    ]


def open_pdf():
    try:
        import fitz
    except ImportError:
        if REQUIRE:
            raise AssertionError(
                "RAINTECH_REQUIRE_NIST=1 but PyMuPDF is not installed; "
                "install catalog/requirements-extraction.txt"
            )
        raise unittest.SkipTest("PyMuPDF is not installed")
    if not NIST_PDF.exists():
        raise AssertionError(f"{NIST_PDF} is missing; the source must stay pinned")
    return fitz.open(NIST_PDF)


class CitationResolutionTest(unittest.TestCase):
    """NIST cites a standard by its containing paragraph, the catalog by record."""

    def test_a_deeper_nested_standard_resolves_through_its_container(self):
        self.assertTrue(resolve_nist_citation("164.310(a)", "164.310(a)(1)"))
        self.assertTrue(resolve_nist_citation("164.308(a)(1)", "164.308(a)(1)(i)"))
        self.assertTrue(resolve_nist_citation("164.316(b)", "164.316(b)(1)"))
        self.assertTrue(resolve_nist_citation("164.312(e)(1)", "164.312(e)(1)"))

    def test_a_sibling_standard_never_resolves_to_its_neighbour(self):
        """The defect in one line: (a)(1) must not answer for (a)(2)."""
        self.assertFalse(resolve_nist_citation("164.308(a)(1)", "164.308(a)(2)"))
        self.assertFalse(resolve_nist_citation("164.308(a)", "164.308(a)(2)"))
        self.assertFalse(resolve_nist_citation("164.310(a)", "164.310(b)"))


class SectionBoundsTest(unittest.TestCase):
    def test_every_security_standard_resolves_to_a_distinct_section(self):
        doc = open_pdf()
        standards = security_standards()
        self.assertEqual(len(standards), 22)

        starts: dict[int, str] = {}
        unresolved: list[str] = []
        for standard in standards:
            start, end = nist_section_bounds(doc, standard)
            if start < 0:
                unresolved.append(standard)
                continue
            self.assertGreater(
                end, start, f"{standard} resolved to an empty page range"
            )
            clash = starts.get(start)
            self.assertIsNone(
                clash,
                f"{standard} and {clash} resolved to the same section at page {start}",
            )
            starts[start] = standard

        self.assertEqual(unresolved, [], "800-66r2 documents all 22 standards")

    def test_headings_are_parsed_once_from_the_body_not_the_contents(self):
        doc = open_pdf()
        headings = nist_headings(doc)
        self.assertEqual(len(headings), 22)
        citations = [citation for _, _, citation, _ in headings]
        self.assertEqual(
            len(set(citations)),
            22,
            "a heading matched twice means the table of contents leaked in",
        )
        pages = [page for _, _, _, page in headings]
        self.assertEqual(pages, sorted(pages), "headings must be ordered by page")


class ExtractionCorpusTest(unittest.TestCase):
    def test_no_two_standards_extract_the_same_prompts(self):
        """The corpus-level check the single-standard sample could not make."""
        open_pdf()
        by_prompts: dict[tuple[str, ...], str] = {}
        for standard in security_standards():
            prompts, _ = extract_nist_prompts(standard)
            key = tuple(prompt.text for prompt in prompts)
            self.assertNotEqual(key, (), f"{standard} extracted no prompts")
            clash = by_prompts.get(key)
            self.assertIsNone(
                clash,
                f"{standard} extracted the same prompts as {clash}",
            )
            by_prompts[key] = standard

    def test_raw_prompt_counts_match_the_verified_extraction(self):
        open_pdf()
        counts = {
            standard: len(extract_nist_prompts(standard)[0])
            for standard in security_standards()
        }
        self.assertEqual(counts, EXPECTED_RAW_COUNTS)
        self.assertEqual(sum(counts.values()), 443)


class SecurityRoutingTest(unittest.TestCase):
    """The general routing rule, measured across all 22 standards.

    The rule it implements was approved July 28, 2026: a key activity that
    identifies an implementation specification routes its questions there;
    genuinely standard-wide activities stay on the parent as guidance.
    """

    _routing = None

    def routing(self):
        # Extracting all 22 sections takes seconds, so it is done once for the
        # whole class rather than once per assertion.
        if SecurityRoutingTest._routing is None:
            open_pdf()
            from hipaa_prompts import build_security_routing

            SecurityRoutingTest._routing = build_security_routing()
        return SecurityRoutingTest._routing

    def test_routing_covers_the_corpus_without_warnings(self):
        routing, warnings = self.routing()
        self.assertEqual(len(routing), 22)
        self.assertEqual(warnings, [])

    def test_every_implementation_specification_receives_prompts(self):
        """An empty determination is a gap in the walkthrough, not a result."""
        routing, _ = self.routing()
        empty = [
            record_id
            for standard_id, entry in routing.items()
            for record_id, prompts in entry["records"].items()
            if not prompts and record_id != standard_id
        ]
        self.assertEqual(empty, [])

    def test_no_prompt_is_dropped_or_duplicated_without_cause(self):
        """Routing moves prompts; it must not lose them.

        One question above the raw total is expected and is the only one:
        164.308(a)(7)(i) asks whether the contingency plan "address[es]
        disaster recovery and data backup", naming two specifications, so it
        informs both determinations.
        """
        routing, _ = self.routing()
        raw = sum(entry["raw_prompt_count"] for entry in routing.values())
        routed = sum(
            len(prompts)
            for entry in routing.values()
            for prompts in entry["records"].values()
        )
        self.assertEqual(raw, 443)
        self.assertEqual(routed, 444)

    def test_a_bare_standard_keeps_every_prompt_on_itself(self):
        """With no specifications there is nowhere else a determination lives."""
        routing, _ = self.routing()
        for standard_id in ("164.308(a)(2)", "164.310(b)", "164.316(a)"):
            entry = routing[standard_id]
            self.assertEqual(list(entry["records"]), [standard_id])
            self.assertEqual(
                len(entry["records"][standard_id]), entry["raw_prompt_count"]
            )

    def test_collectively_marked_activities_split_by_question(self):
        """164.312(a)(1) marks logoff and encryption in one activity.

        Attaching all eight questions to both records would put four
        irrelevant questions on each determination.
        """
        routing, _ = self.routing()
        records = routing["164.312(a)(1)"]["records"]
        logoff = [p.text for p in records["164.312(a)(2)(iii)"]]
        encryption = [p.text for p in records["164.312(a)(2)(iv)"]]
        self.assertTrue(logoff and encryption)
        self.assertEqual(set(logoff) & set(encryption), set())
        self.assertTrue(any("automatic logoff" in t.lower() for t in logoff))
        self.assertTrue(any("encryption" in t.lower() for t in encryption))

    def test_committed_routing_artifact_is_current(self):
        from hipaa_prompts import render_security_routing

        routing, warnings = self.routing()
        committed = REPO_ROOT / "docs" / "catalogs" / "security-prompt-routing.md"
        self.assertEqual(
            committed.read_text(encoding="utf-8"),
            render_security_routing(routing, warnings),
        )


class PromptLayerReproducibilityTest(unittest.TestCase):
    """The committed layer must be what the pinned sources produce.

    Without this the layer is just a file someone generated once, and the
    'rebuilds from its pinned source' property the catalog already has would
    not extend to the prompts nested beneath it.
    """

    def test_committed_layer_rebuilds_from_its_pinned_sources(self):
        open_pdf()
        from hipaa_prompts import build_prompt_layer

        committed = json.loads(
            (
                REPO_ROOT
                / "catalog"
                / "versions"
                / "hipaa-45cfr164-2026-07-01-prompts.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(build_prompt_layer(), committed)


class SampleReproducibilityTest(unittest.TestCase):
    def test_committed_sample_is_reproducible_from_the_pinned_source(self):
        """The committed fixture had drifted from the script that emits it."""
        open_pdf()
        committed = REPO_ROOT / "catalog" / "spikes" / "prompts-sample.json"
        with tempfile.TemporaryDirectory() as tmp:
            regenerated = Path(tmp) / "prompts-sample.json"
            subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "catalog" / "hipaa_prompts.py"),
                    "--sample",
                    "--out",
                    str(regenerated),
                ],
                check=True,
                capture_output=True,
            )
            self.assertEqual(
                json.loads(regenerated.read_text(encoding="utf-8")),
                json.loads(committed.read_text(encoding="utf-8")),
            )


if __name__ == "__main__":
    unittest.main()
