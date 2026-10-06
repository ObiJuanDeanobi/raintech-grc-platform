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


if __name__ == "__main__":
    unittest.main()
