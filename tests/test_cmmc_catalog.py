"""Structure, provenance, and coexistence tests for the CMMC Level 2 catalog (#30)."""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from cmmc_ingest import EXPORT, OUTPUT, SEED, build, export  # noqa: E402

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# Fictional examples printed in the Assessment Guide itself, not client data.
GUIDE_EXAMPLES = {"riley@acme.com"}
# Same separator throughout, so citations like DFARS 252.204-7012 do not match.
PHONE = re.compile(r"\(\d{3}\)\s?\d{3}-\d{4}\b|\b\d{3}([-.])\d{3}\1\d{4}\b")


class CmmcCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = json.loads(SEED.read_text(encoding="utf-8"))
        cls.catalog = json.loads(OUTPUT.read_text(encoding="utf-8"))
        cls.records = cls.catalog["records"]

    def test_counts(self) -> None:
        self.assertEqual(
            self.catalog["counts"], {"domains": 14, "requirements": 110, "objectives": 320}
        )
        self.assertEqual(len(self.records), 430)

    def test_identifiers_are_published_stable_and_unique(self) -> None:
        ids = [r["id"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        published = {r["id"] for r in self.seed["requirements"]} | {
            o["id"] for o in self.seed["objectives"]
        }
        self.assertEqual(set(ids), published)

    def test_every_objective_maps_to_one_requirement(self) -> None:
        requirements = {r["id"] for r in self.records if r["record_type"] == "requirement"}
        objectives = [r for r in self.records if r["record_type"] == "objective"]
        self.assertTrue(all(o["parent_id"] in requirements for o in objectives))
        self.assertEqual({o["parent_id"] for o in objectives}, requirements)
        self.assertTrue(
            all(r["parent_id"] is None for r in self.records if r["record_type"] == "requirement")
        )

    def test_official_fields_carry_provenance(self) -> None:
        authority = self.catalog["framework_version"]["authority"]
        self.assertIn("Assessment Guide", authority)
        self.assertTrue(all(r["authority"] == authority for r in self.records))
        self.assertTrue(all(r["text"].strip() for r in self.records))

    def test_rebuild_is_deterministic_and_matches_committed_files(self) -> None:
        catalog, discrepancies = build(self.seed)
        self.assertEqual(catalog, self.catalog)
        self.assertEqual(export(catalog, discrepancies), EXPORT.read_text(encoding="utf-8"))
        text_fields = {
            (r["id"], f): r[f]
            for r in self.records
            for f in ("title", "text", "potential_methods", "discussion", "further_discussion")
            if f in r
        }
        # Text is carried verbatim; artifacts are reported, never corrected.
        seeded = {(r["id"], "text"): r["text"] for r in self.seed["requirements"]}
        for key, value in seeded.items():
            self.assertEqual(text_fields[key], value)

    def test_derived_artifacts_contain_no_contact_identifiers(self) -> None:
        for path in (OUTPUT, EXPORT):
            content = path.read_text(encoding="utf-8")
            emails = set(EMAIL.findall(content)) - GUIDE_EXAMPLES
            self.assertEqual(emails, set(), path)
            self.assertIsNone(PHONE.search(content), path)
            denylist = os.environ.get("RAINTECH_CLIENT_DENYLIST")
            if denylist:
                for name in Path(denylist).read_text(encoding="utf-8").splitlines():
                    if name.strip():
                        self.assertNotIn(name.strip().lower(), content.lower(), path)


if __name__ == "__main__":
    unittest.main()
