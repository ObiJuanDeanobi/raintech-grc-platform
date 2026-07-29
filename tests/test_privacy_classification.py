"""Behaviour tests for Privacy and Breach child-paragraph role classification.

These need only the committed subpart XML, so they run in the standard-library
CI job with no PyMuPDF and no network.

The roles were approved July 28, 2026: an operative requirement is an
assessment_check and renders a checkbox; an exception, exemption, or scope/N/A
condition is an applicability_note; a structural lead-in or optional permission
is context. Only an assessment_check renders a checkbox, and no role carries a
status or produces a finding.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from hipaa_prompts import (  # noqa: E402
    APPLICABILITY_NOTE,
    ASSESSMENT_CHECK,
    CONTEXT,
    build_privacy_classification,
    classify_privacy_paragraphs,
    render_privacy_classification,
)

ARTIFACT = REPO_ROOT / "docs" / "catalogs" / "privacy-breach-classification.md"


class ClassifierUnitTest(unittest.TestCase):
    def roles(self, paragraphs):
        return [role for role, _ in classify_privacy_paragraphs(paragraphs)]

    def test_a_repeated_path_is_classified_independently(self):
        """A labelled lead-in and its quoted text share a CFR path.

        A path-keyed result collapses them; the classifier must not.
        """
        paragraphs = [
            ("(b)(1)(i)", "Header.", "Header. The notice must contain the statement:"),
            ("(b)(1)(i)", "", "THIS NOTICE DESCRIBES HOW INFORMATION MAY BE USED."),
        ]
        result = classify_privacy_paragraphs(paragraphs)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], ASSESSMENT_CHECK)

    def test_enumerated_items_under_an_obligation_leadin_are_checks(self):
        paragraphs = [
            ("(b)(1)(ii)", "Uses and disclosures.", "Uses and disclosures. The notice must contain:"),
            ("(b)(1)(ii)(A)", "", "A description of the types of uses the entity is permitted to make."),
            ("(b)(1)(ii)(B)", "", "A description of each of the other purposes required by law."),
        ]
        self.assertEqual(
            self.roles(paragraphs),
            [CONTEXT, ASSESSMENT_CHECK, ASSESSMENT_CHECK],
        )

    def test_an_exception_and_its_descendants_are_applicability_notes(self):
        paragraphs = [
            ("(a)(3)", "Exception for group health plans.", "Exception for group health plans. An individual has a right to notice."),
            ("(a)(3)(i)", "", "From the group health plan, if the individual does not receive benefits."),
            ("(a)(4)", "Exception for inmates.", "Exception for inmates. An inmate does not have a right to notice under this section."),
        ]
        self.assertEqual(
            self.roles(paragraphs),
            [APPLICABILITY_NOTE, APPLICABILITY_NOTE, APPLICABILITY_NOTE],
        )

    def test_an_obligation_inside_an_exception_subtree_stays_a_check(self):
        """Inheritance yields to an item's own operative obligation."""
        paragraphs = [
            ("(a)(3)", "Exception for group health plans.", "Exception for group health plans."),
            ("(a)(3)(ii)", "", "A plan described in this paragraph must maintain a notice and provide it on request."),
        ]
        self.assertEqual(self.roles(paragraphs)[1], ASSESSMENT_CHECK)

    def test_a_conditional_obligation_is_a_check(self):
        paragraphs = [
            ("(c)(2)(i)(B)", "", "In an emergency treatment situation, the provider must furnish notice as soon as practicable."),
        ]
        self.assertEqual(self.roles(paragraphs), [ASSESSMENT_CHECK])

    def test_only_a_genuinely_optional_element_is_context(self):
        paragraphs = [
            ("(b)(2)", "Optional elements.", "Optional elements. The notice may contain additional information."),
            ("(b)(2)(x)", "", "The authorization may contain elements in addition to the required core elements."),
        ]
        self.assertEqual(self.roles(paragraphs), [CONTEXT, CONTEXT])

    def test_a_prohibition_is_a_check_not_an_applicability_note(self):
        paragraphs = [
            ("(b)(4)", "Prohibition on conditioning.", "Prohibition on conditioning. A covered entity may not condition treatment on an authorization."),
        ]
        self.assertEqual(self.roles(paragraphs), [ASSESSMENT_CHECK])


class ClassificationCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classified, cls.warnings = build_privacy_classification()

    def test_covers_the_privacy_and_breach_records_with_children(self):
        self.assertEqual(len(self.classified), 81)
        total = sum(len(e["entries"]) for e in self.classified.values())
        self.assertEqual(total, 721)

    def test_no_operative_obligation_is_hidden_as_non_check(self):
        """A plain must/shall requirement must never lose its checkbox.

        Lead-ins and explicit exceptions are the two intended exceptions: a
        lead-in's obligation is discharged by its children, and an exception is
        a scope statement even when phrased with must/shall.
        """
        hidden = []
        for entry in self.classified.values():
            for item in entry["entries"]:
                if item["role"] == ASSESSMENT_CHECK:
                    continue
                if item["role"] == APPLICABILITY_NOTE:
                    continue
                if "lead-in" in item["role_reason"]:
                    continue
                if re.search(r"\b(?:must|shall)\b", item["text"], re.I):
                    hidden.append(item["cfr_paragraph"])
        self.assertEqual(hidden, [])

    def test_every_entry_quotes_the_regulation(self):
        for entry in self.classified.values():
            for item in entry["entries"]:
                self.assertTrue(item["text"], item["cfr_paragraph"])
                self.assertIn(item["role"], (ASSESSMENT_CHECK, APPLICABILITY_NOTE, CONTEXT))

    def test_committed_artifact_is_current(self):
        self.assertEqual(
            ARTIFACT.read_text(encoding="utf-8"),
            render_privacy_classification(self.classified, self.warnings),
        )


if __name__ == "__main__":
    unittest.main()
