"""CMMC Level 2 scoring data rebuilt from pinned 32 CFR 170.24 / 170.21 text (Issue #105)."""

from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from cmmc_scoring import SCORING_ID, build  # noqa: E402

SCORING_PATH = REPO_ROOT / "catalog" / "versions" / f"{SCORING_ID}.json"


class ScoringDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(SCORING_PATH.read_text(encoding="utf-8"))
        self.values = self.data["requirements"]

    def test_committed_file_matches_rebuild_from_pinned_source(self) -> None:
        self.assertEqual(self.data, build())

    def test_every_catalog_requirement_has_exactly_one_value(self) -> None:
        catalog = json.loads(
            (REPO_ROOT / "catalog/versions/cmmc-l2-ag-v2.13.json").read_text(encoding="utf-8")
        )
        requirements = [r["id"] for r in catalog["records"] if r["record_type"] == "requirement"]
        self.assertEqual(list(self.values), requirements)
        self.assertEqual(self.data["catalog_content_sha256"], catalog["content_sha256"])

    def test_value_distribution_follows_the_regulation(self) -> None:
        fixed = Counter(v["points"] for v in self.values.values() if v["rule"] == "fixed")
        self.assertEqual(fixed, {5: 42, 3: 14, 1: 51})
        self.assertEqual(
            {k for k, v in self.values.items() if v["rule"] == "partial"},
            {"IA.L2-3.5.3", "SC.L2-3.13.11"},
        )
        self.assertEqual(
            [k for k, v in self.values.items() if v["rule"] == "ssp_required"], ["CA.L2-3.12.4"]
        )
        self.assertEqual(self.data["maximum_score"], 110)
        self.assertEqual(self.data["minimum_score"], -203)

    def test_spot_values(self) -> None:
        self.assertEqual(self.values["AC.L2-3.1.1"]["points"], 5)
        self.assertEqual(self.values["AC.L2-3.1.19"]["points"], 3)
        self.assertEqual(self.values["IA.L2-3.5.1"]["points"], 5)
        self.assertEqual(self.values["AC.L2-3.1.3"]["points"], 1)
        self.assertEqual(self.values["IA.L2-3.5.3"]["points_by_implementation"], {"partial": 3, "none": 5})

    def test_every_value_cites_its_paragraph(self) -> None:
        for requirement_id, value in self.values.items():
            self.assertRegex(value["source"], r"^32 CFR 170\.24\(c\)\(2\)\(i\)\(B\)\(\d\)", requirement_id)

    def test_irregular_source_ids_are_reported(self) -> None:
        printed = {d["printed"] for d in self.data["discrepancies"]}
        self.assertEqual(printed, {"IA-L2-3.5.1", "IA-L2-3.5.2", "AC.L2- 3.1.19"})

    def test_conditional_poam_rules(self) -> None:
        rules = self.data["conditional_poam"]
        self.assertEqual(rules["minimum_score_ratio"], 0.8)
        self.assertEqual(rules["maximum_points"], 1)
        self.assertEqual(
            rules["excluded"],
            ["AC.L2-3.1.20", "AC.L2-3.1.22", "CA.L2-3.12.4", "PE.L2-3.10.3", "PE.L2-3.10.4", "PE.L2-3.10.5"],
        )

    def test_conditional_checks_cite_their_paragraphs(self) -> None:
        self.assertEqual(
            self.data["conditional_poam"]["paragraphs"],
            {
                "minimum_score": "32 CFR 170.21(a)(2)(i)",
                "maximum_points": "32 CFR 170.21(a)(2)(ii)",
                "excluded": "32 CFR 170.21(a)(2)(iii)",
            },
        )


class MethodologyReconciliationTests(unittest.TestCase):
    """The regulation-derived values agree with the pinned DoD Assessment Methodology.

    docs/sources/cmmc-dfars/DoD-NIST-SP-800-171-Assessment-Methodology-v1.2.1.pdf
    (sha256 dd88416c...0835). The lists below are transcribed from it for
    cross-checking only; scoring still reads the 32 CFR 170.24 build (Issue #141).
    """

    # Section 5(d)(i)(1)-(2), p. 6: 5-point basic and derived requirements.
    FIVE = ["3.1.1", "3.1.2", "3.2.1", "3.2.2", "3.3.1", "3.4.1", "3.4.2", "3.5.1", "3.5.2", "3.6.1", "3.6.2", "3.7.2", "3.8.3", "3.9.2", "3.10.1", "3.10.2", "3.12.1", "3.12.3", "3.13.1", "3.13.2", "3.14.1", "3.14.2", "3.14.3", "3.1.12", "3.1.13", "3.1.16", "3.1.17", "3.1.18", "3.3.5", "3.4.5", "3.4.6", "3.4.7", "3.4.8", "3.5.10", "3.7.5", "3.8.7", "3.11.2", "3.13.5", "3.13.6", "3.13.15", "3.14.4", "3.14.6"]
    # Section 5(d)(ii)(1)-(2), p. 6: 3-point basic and derived requirements.
    THREE = ["3.3.2", "3.7.1", "3.8.1", "3.8.2", "3.9.1", "3.11.1", "3.12.2", "3.1.5", "3.1.19", "3.7.4", "3.8.8", "3.13.8", "3.14.5", "3.14.7"]

    def setUp(self) -> None:
        data = json.loads(SCORING_PATH.read_text(encoding="utf-8"))
        self.values = {key.split("-", 1)[1]: value for key, value in data["requirements"].items()}

    def test_five_and_three_point_lists_match(self) -> None:
        fixed = {k: v["points"] for k, v in self.values.items() if v["rule"] == "fixed"}
        self.assertEqual({k for k, v in fixed.items() if v == 5}, set(self.FIVE))
        self.assertEqual({k for k, v in fixed.items() if v == 3}, set(self.THREE))
        # Section 5(d)(iii), pp. 6-7: all remaining derived requirements are 1 point.
        self.assertEqual(len([v for v in fixed.values() if v == 1]), 110 - 42 - 14 - 3)

    def test_partial_credit_and_ssp_match(self) -> None:
        # Section 5(e)(i)-(ii), p. 7; Annex A p. 15 (3.5.3) and p. 19 (3.13.11): "3 to 5".
        for requirement in ("3.5.3", "3.13.11"):
            self.assertEqual(
                self.values[requirement]["points_by_implementation"], {"partial": 3, "none": 5}
            )
        # Section 5(g)(i), p. 7; Annex A p. 18: 3.12.4 is "NA" (no point value).
        self.assertEqual(self.values["3.12.4"]["rule"], "ssp_required")
        self.assertNotIn("points", self.values["3.12.4"])


if __name__ == "__main__":
    unittest.main()
