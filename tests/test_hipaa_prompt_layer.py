"""Acceptance tests for the full HIPAA prompt layer and its export.

The layer adds guidance beneath the catalog. It must not disturb what the
catalog asserts: 194 records, their citations, their text, and their
determinations are unchanged by anything here.

These read the committed layer fixture, so they need no PyMuPDF and run in the
standard-library CI job. Rebuilding the layer from its pinned sources is a
separate step that does need the PDF.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from hipaa_export import render  # noqa: E402

CATALOG_PATH = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"
LAYER_PATH = (
    REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01-prompts.json"
)
EXPORT_PATH = REPO_ROOT / "docs" / "catalogs" / "hipaa-45cfr164-2026-07-01.md"

ROLES = {"assessment_check", "applicability_note", "context"}


class PromptLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
        cls.records = {r["id"]: r for r in cls.catalog["records"]}

    def prompts(self):
        for record_id, entry in self.layer["entries"].items():
            for prompt in entry["prompts"]:
                yield record_id, prompt

    def test_the_catalog_is_unchanged_at_194_records(self):
        """This adds a layer; it does not restructure the catalog."""
        self.assertEqual(len(self.catalog["records"]), 194)
        self.assertEqual(
            self.layer["framework_version"],
            self.catalog["framework_version"]["id"],
        )

    def test_every_prompt_attaches_to_a_real_record_by_citation(self):
        """Never an invented identifier."""
        for record_id, _ in self.prompts():
            self.assertIn(record_id, self.records)

    def test_no_prompt_carries_a_status_or_can_produce_a_finding(self):
        status_fields = {"status", "determination", "finding", "result", "met"}
        for record_id, prompt in self.prompts():
            self.assertEqual(
                set(prompt) & status_fields,
                set(),
                f"{record_id}: a prompt must never carry a status",
            )

    def test_every_prompt_records_its_source_and_revision(self):
        sources = {source["id"]: source for source in self.layer["sources"]}
        self.assertEqual(set(sources), {"nist-800-66r2", "cfr-enumeration"})
        for source in sources.values():
            self.assertTrue(source["revision"])
        for record_id, prompt in self.prompts():
            self.assertTrue(prompt["source"], record_id)
            self.assertTrue(
                prompt["cfr_paragraph"] or prompt["source_detail"],
                f"{record_id}: a prompt must say where it came from",
            )

    def test_every_prompt_has_a_known_presentation_role(self):
        for record_id, prompt in self.prompts():
            self.assertIn(prompt["role"], ROLES, record_id)

    def test_cfr_prompts_are_citable_to_a_paragraph(self):
        for record_id, entry in self.layer["entries"].items():
            if entry["path"] != "cfr-enumeration":
                continue
            for prompt in entry["prompts"]:
                self.assertTrue(
                    prompt["cfr_paragraph"].startswith("45 CFR "),
                    f"{record_id}: quoted regulation must cite its paragraph",
                )

    def test_records_without_prompts_are_reported_and_explained(self):
        """Not silently empty."""
        without = self.layer["records_without_prompts"]
        self.assertTrue(without)
        for item in without:
            self.assertIn(item["record_id"], self.records)
            self.assertTrue(item["reason"].strip())
            self.assertNotIn(item["record_id"], self.layer["entries"])

    def test_every_record_is_either_prompted_or_explained(self):
        covered = set(self.layer["entries"])
        explained = {item["record_id"] for item in self.layer["records_without_prompts"]}
        self.assertEqual(covered | explained, set(self.records))
        self.assertEqual(covered & explained, set())

    def test_no_entry_is_empty(self):
        for record_id, entry in self.layer["entries"].items():
            self.assertTrue(entry["prompts"], record_id)

    def test_counts_match_the_content(self):
        counts = self.layer["counts"]
        self.assertEqual(counts["records_total"], 194)
        self.assertEqual(counts["records_with_prompts"], len(self.layer["entries"]))
        self.assertEqual(
            counts["prompts_total"],
            sum(len(e["prompts"]) for e in self.layer["entries"].values()),
        )
        self.assertEqual(
            counts["records_with_prompts"] + counts["records_without_prompts"],
            194,
        )


class ExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8"))

    def test_committed_export_nests_prompts_under_their_record(self):
        self.assertEqual(
            EXPORT_PATH.read_text(encoding="utf-8"),
            render(self.catalog, self.layer),
        )

    def test_only_assessment_checks_render_a_checkbox(self):
        """A note or context entry is read, not ticked."""
        rendered = render(self.catalog, self.layer)
        lines = rendered.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith(("- [ ]", "-")) or "_(" not in stripped:
                continue
            if "_(context)_" in stripped or "_(applicability)_" in stripped:
                self.assertFalse(
                    stripped.startswith("- [ ]"),
                    f"non-check rendered a checkbox: {stripped[:80]}",
                )

    def test_the_export_still_renders_without_a_prompt_layer(self):
        """The catalog export predates prompts and must not depend on them."""
        rendered = render(self.catalog)
        self.assertIn("45 CFR 164.308(a)(1)(i)", rendered)
        self.assertNotIn("_(context)_", rendered)


if __name__ == "__main__":
    unittest.main()
