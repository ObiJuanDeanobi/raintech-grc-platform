"""Structure, provenance, and sanitization tests for the pinned CMMC L2 catalog.

The catalog is migrated from the archived legacy seed, not re-extracted. These
tests rebuild it from that seed and compare it to the committed file, so any
drift in either is caught. No network calls.
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))

from cmmc_export import render  # noqa: E402
from cmmc_ingest import FRAMEWORK_ID, SEED_PATH, CatalogError, build  # noqa: E402

CATALOG_PATH = REPO_ROOT / "catalog" / "versions" / f"{FRAMEWORK_ID}.json"
EXPORT_PATH = REPO_ROOT / "docs" / "catalogs" / f"{FRAMEWORK_ID}.md"
HIPAA_PATH = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"

# Published requirement counts per domain in the CMMC Assessment Guide L2 v2.13.
PUBLISHED_DOMAIN_COUNTS = {
    "AC": 22, "AT": 3, "AU": 9, "CM": 9, "IA": 11, "IR": 3, "MA": 6,
    "MP": 9, "PS": 2, "PE": 6, "RA": 3, "CA": 4, "SC": 16, "SI": 7,
}

# Client-identifier patterns. Every match in a committed derived artifact must
# be listed here with the reason it is not a client identifier.
IDENTIFIER_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "phone": re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"),
    "ipv4": re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    "company": re.compile(r"\b[A-Z][\w&]+,? (?:LLC|Inc\.?|Corp\.?|Corporation|Ltd\.?)(?!\w)"),
    "url": re.compile(r"https?://[^\s)\]\"<>]+"),
}
ALLOWED_MATCHES = {
    "riley@acme.com": "Fictional example username in the Guide's IA further discussion.",
    "252.204-7012": "DFARS clause number, not a phone number.",
    "https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf": "Official source URL.",
}


def load() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


class RebuildTests(unittest.TestCase):
    def test_committed_catalog_matches_rebuild_from_seed(self) -> None:
        self.assertEqual(load(), build())

    def test_rebuild_is_deterministic(self) -> None:
        self.assertEqual(build(), build())

    def test_committed_export_matches_render(self) -> None:
        self.assertEqual(EXPORT_PATH.read_text(encoding="utf-8"), render(load()))

    def test_structural_faults_are_refused_not_repaired(self) -> None:
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        faults = {
            "duplicate objective": lambda s: s["objectives"].append(copy.deepcopy(s["objectives"][0])),
            "orphan objective": lambda s: s["objectives"][0].update(requirement_id="AC.L2-3.1.99"),
            "renamed requirement": lambda s: s["requirements"][0].update(id="AC.L2-3.1.1x"),
            "missing requirement": lambda s: s["requirements"].pop(),
        }
        for name, mutate in faults.items():
            with self.subTest(name):
                broken = copy.deepcopy(seed)
                mutate(broken)
                with tempfile.TemporaryDirectory() as directory:
                    target = Path(directory) / "seed.json"
                    target.write_text(json.dumps(broken), encoding="utf-8")
                    with self.assertRaises(CatalogError):
                        build(target)


class StructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load()
        self.records = self.catalog["records"]

    def test_counts(self) -> None:
        types = Counter(r["record_type"] for r in self.records)
        self.assertEqual(types, {"requirement": 110, "objective": 320})
        self.assertEqual(len({r["domain_code"] for r in self.records}), 14)
        self.assertEqual(self.catalog["counts"]["by_domain"], PUBLISHED_DOMAIN_COUNTS)

    def test_ids_unique_and_stable(self) -> None:
        ids = [r["id"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(ids), {r["id"] for r in seed["requirements"]} | {o["id"] for o in seed["objectives"]}
        )

    def test_every_objective_has_exactly_one_known_requirement(self) -> None:
        requirements = {r["id"] for r in self.records if r["record_type"] == "requirement"}
        for record in self.records:
            if record["record_type"] == "objective":
                self.assertIn(record["parent_id"], requirements)
                self.assertTrue(record["id"].startswith(record["parent_id"]))
            else:
                self.assertIsNone(record["parent_id"])
        parents = {r["parent_id"] for r in self.records if r["parent_id"]}
        self.assertEqual(parents, requirements)

    def test_objectives_follow_their_requirement(self) -> None:
        current = None
        for record in self.records:
            if record["record_type"] == "requirement":
                current = record["id"]
            else:
                self.assertEqual(record["parent_id"], current)

    def test_official_fields_have_declared_authority(self) -> None:
        authority = self.catalog["field_authority"]
        for record in self.records:
            for field in ("title", "text", "assessment_methods", "discussion", "further_discussion"):
                if field in record:
                    self.assertIn(f"{record['record_type']}.{field}", authority)
                    self.assertTrue(record[field].strip(), f"{record['id']}.{field}")
        self.assertFalse(any("raintech" in a.lower() for a in authority.values()))

    def test_provenance_and_hash(self) -> None:
        version = self.catalog["framework_version"]
        self.assertEqual(version["source_title"], "CMMC Assessment Guide Level 2 Version 2.13")
        self.assertRegex(version["migrated_from_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.catalog["content_sha256"], r"^[0-9a-f]{64}$")

    def test_discrepancies_reference_real_records(self) -> None:
        ids = {r["id"] for r in self.records}
        checks = self.catalog["discrepancy_checks"]
        for item in self.catalog["discrepancies"]:
            self.assertIn(item["record_id"], ids)
            self.assertIn(item["check"], checks)

    def test_coexists_with_hipaa(self) -> None:
        hipaa = json.loads(HIPAA_PATH.read_text(encoding="utf-8"))
        self.assertNotEqual(hipaa["framework_version"]["id"], FRAMEWORK_ID)
        self.assertFalse({r["id"] for r in hipaa["records"]} & {r["id"] for r in self.records})
        self.assertEqual(len(hipaa["records"]), 194)


class SanitizationTests(unittest.TestCase):
    def test_no_client_identifiers_in_derived_artifacts(self) -> None:
        for path in (CATALOG_PATH, EXPORT_PATH):
            text = path.read_text(encoding="utf-8")
            for name, pattern in IDENTIFIER_PATTERNS.items():
                for match in pattern.finditer(text):
                    with self.subTest(path=path.name, kind=name, match=match.group(0)):
                        self.assertIn(match.group(0), ALLOWED_MATCHES)

    def test_scan_detects_identifiers(self) -> None:
        sample = "Contact jane@client.example, 555-123-4567, 10.0.0.5, Northwind Traders, LLC"
        found = {name for name, p in IDENTIFIER_PATTERNS.items() if p.search(sample)}
        self.assertEqual(found, {"email", "phone", "ipv4", "company"})


if __name__ == "__main__":
    unittest.main()
