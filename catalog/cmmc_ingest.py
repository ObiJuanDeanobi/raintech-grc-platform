"""Build the pinned CMMC Level 2 catalog from the archived legacy seed.

This is a migration, not an extraction. The legacy evidence tracker already
extracted the CMMC Assessment Guide Level 2 v2.13 into
``legacy/evidence-tracker/cmmc_tracker/data/cmmc_l2_seed.json`` (14 domains,
110 requirements, 320 objectives). This script maps that seed into the shared
catalog record shape (ADR 0012) without changing published identifiers.

Text is carried verbatim. Extraction artifacts in the seed (lowercased
"[cui Data]" titles, section headings and footnote markers inside fields, page
headers leaking into the next field) are *reported* in ``discrepancies`` and
the reconciliation report, never corrected here.

The seed's per-objective ``evidence_examples`` are not carried. They are a
truncated copy of the requirement-level NIST SP 800-171A Examine objects,
which survive in full in ``assessment_methods``, plus a legacy placeholder for
15 objectives that is not framework text.

Usage:
    python catalog/cmmc_ingest.py --out catalog/versions/cmmc-l2-ag-v2.13.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_RELATIVE = "legacy/evidence-tracker/cmmc_tracker/data/cmmc_l2_seed.json"
SEED_PATH = REPO_ROOT / SEED_RELATIVE
SEED_COMMIT = "11fbb32"
FRAMEWORK_ID = "cmmc-l2-ag-v2.13"

EXPECTED_DOMAINS = 14
EXPECTED_REQUIREMENTS = 110
EXPECTED_OBJECTIVES = 320

REQUIREMENT_ID_RE = re.compile(r"^(?P<domain>[A-Z]{2})\.L2-3\.(?P<family>\d+)\.(?P<number>\d+)$")
OBJECTIVE_LETTER_RE = re.compile(r"^[a-z]$")
PAGE_HEADER_RE = re.compile(r"[A-Z]{2}\.L2-3\.\d+\.\d+ [–-] ")
FOOTNOTE_RE = re.compile(r"\]\s?\d+\b")

# Which authority each carried field comes from. RainTech practitioner
# guidance is deliberately absent: the seed holds none, and #31 adds it as a
# separately attributed layer.
FIELD_AUTHORITY = {
    "requirement.text": "NIST SP 800-171 Rev. 2 security requirement, as quoted in the CMMC Assessment Guide L2 v2.13",
    "requirement.title": "CMMC Assessment Guide L2 v2.13 practice short name",
    "requirement.assessment_methods": "NIST SP 800-171A potential assessment methods and objects, as quoted in the CMMC Assessment Guide L2 v2.13",
    "requirement.discussion": "NIST SP 800-171 Rev. 2 discussion, as quoted in the CMMC Assessment Guide L2 v2.13",
    "requirement.further_discussion": "CMMC Assessment Guide L2 v2.13 further discussion (DoD)",
    "objective.title": "Generated label from the published objective letter; not Guide text",
    "objective.text": "NIST SP 800-171A assessment objective (determination statement), as quoted in the CMMC Assessment Guide L2 v2.13",
}

ARTIFACT_CHECKS = {
    "lowercase_cui_title": "Title reads '[cui Data]'; the Guide prints '[CUI Data]'.",
    "heading_prefix": "Field begins with the Guide's section heading.",
    "footnote_marker": "Field contains a footnote reference number after a bracketed citation.",
    "page_header_leak": "Field contains a requirement page header ('XX.L2-3.n.n – Title').",
}


class CatalogError(ValueError):
    """The seed violates a structural invariant. Never repaired silently."""


def _check_structure(seed: dict[str, Any]) -> None:
    domains, requirements, objectives = seed["domains"], seed["requirements"], seed["objectives"]
    problems: list[str] = []
    counts = (len(domains), len(requirements), len(objectives))
    if counts != (EXPECTED_DOMAINS, EXPECTED_REQUIREMENTS, EXPECTED_OBJECTIVES):
        problems.append(f"counts {counts} != (14, 110, 320)")
    domain_codes = [d["code"] for d in domains]
    requirement_ids = [r["id"] for r in requirements]
    objective_ids = [o["id"] for o in objectives]
    for label, ids in (("domain", domain_codes), ("requirement", requirement_ids), ("objective", objective_ids)):
        duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
        if duplicates:
            problems.append(f"duplicate {label} ids: {duplicates}")
    if set(requirement_ids) & set(objective_ids):
        problems.append("requirement and objective ids overlap")
    known_requirements = set(requirement_ids)
    for requirement in requirements:
        match = REQUIREMENT_ID_RE.match(requirement["id"])
        if not match:
            problems.append(f"unpublished requirement id shape: {requirement['id']}")
        elif match["domain"] != requirement["domain_code"]:
            problems.append(f"{requirement['id']} filed under {requirement['domain_code']}")
        if requirement["domain_code"] not in domain_codes:
            problems.append(f"{requirement['id']} has orphan domain {requirement['domain_code']}")
    letters: dict[str, list[str]] = {}
    for objective in objectives:
        parent = objective["requirement_id"]
        if parent not in known_requirements:
            problems.append(f"orphan objective {objective['id']} -> {parent}")
        if not OBJECTIVE_LETTER_RE.match(objective["letter"]) or objective["id"] != parent + objective["letter"]:
            problems.append(f"objective id {objective['id']} != {parent}+{objective['letter']}")
        letters.setdefault(parent, []).append(objective["letter"])
    for requirement_id in requirement_ids:
        found = letters.get(requirement_id, [])
        if not found:
            problems.append(f"{requirement_id} has no objectives")
        elif found != [chr(ord("a") + i) for i in range(len(found))]:
            problems.append(f"{requirement_id} objective letters not contiguous: {found}")
    for record in [*requirements, *objectives]:
        if not record["text"].strip():
            problems.append(f"{record['id']} has empty text")
    if problems:
        raise CatalogError("; ".join(problems))


def _artifacts(record_id: str, field: str, value: str) -> list[dict[str, str]]:
    found = []
    if field == "title" and "[cui Data]" in value:
        found.append("lowercase_cui_title")
    if field in {"assessment_methods", "discussion", "further_discussion"}:
        if re.match(r"^(POTENTIAL ASSESSMENT METHODS|DISCUSSION|FURTHER DISCUSSION)", value):
            found.append("heading_prefix")
        if FOOTNOTE_RE.search(value[:120]):
            found.append("footnote_marker")
    if PAGE_HEADER_RE.search(value):
        found.append("page_header_leak")
    return [{"record_id": record_id, "field": field, "check": check} for check in found]


def build(seed_path: Path = SEED_PATH) -> dict[str, Any]:
    raw = seed_path.read_bytes()
    seed = json.loads(raw)
    _check_structure(seed)
    domains = {d["code"]: d for d in seed["domains"]}
    domain_order = sorted(domains, key=lambda code: domains[code]["sort_order"])
    objectives_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for objective in seed["objectives"]:
        objectives_by_requirement.setdefault(objective["requirement_id"], []).append(objective)

    def requirement_key(requirement: dict[str, Any]) -> tuple[int, int, int]:
        match = REQUIREMENT_ID_RE.match(requirement["id"])
        assert match
        return (domain_order.index(match["domain"]), int(match["family"]), int(match["number"]))

    records: list[dict[str, Any]] = []
    discrepancies: list[dict[str, str]] = []
    for requirement in sorted(seed["requirements"], key=requirement_key):
        domain = domains[requirement["domain_code"]]
        fields = {
            "title": requirement["name"],
            "text": requirement["text"],
            "assessment_methods": requirement["potential_methods"],
            "discussion": requirement["discussion"],
            "further_discussion": requirement["further_discussion"],
        }
        for field, value in fields.items():
            discrepancies.extend(_artifacts(requirement["id"], field, value))
        records.append(
            {
                "id": requirement["id"],
                "citation": requirement["id"],
                "work_area": domain["name"],
                "domain_code": domain["code"],
                "record_type": "requirement",
                "parent_id": None,
                "designation": None,
                **fields,
            }
        )
        for objective in objectives_by_requirement[requirement["id"]]:
            discrepancies.extend(_artifacts(objective["id"], "text", objective["text"]))
            records.append(
                {
                    "id": objective["id"],
                    "citation": f"{requirement['id']}[{objective['letter']}]",
                    "work_area": domain["name"],
                    "domain_code": domain["code"],
                    "record_type": "objective",
                    "parent_id": requirement["id"],
                    "designation": None,
                    "title": f"Objective [{objective['letter']}]",
                    "text": objective["text"],
                }
            )

    placeholder_examples = sorted(
        o["id"]
        for o in seed["objectives"]
        if any("objective-specific evidence" in example for example in o["evidence_examples"])
    )
    content_hash = sha256(
        json.dumps(records, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "framework": "CMMC",
        "framework_version": {
            "id": FRAMEWORK_ID,
            "authority": "CMMC Level 2 (32 CFR Part 170); NIST SP 800-171 Rev. 2 and SP 800-171A",
            "source_title": seed["source"]["title"],
            "source_url": seed["source"]["url"],
            "source_retrieved": "Not recorded by the legacy extraction",
            "migrated_from": SEED_RELATIVE,
            "migrated_from_commit": SEED_COMMIT,
            "migrated_from_sha256": sha256(raw).hexdigest(),
        },
        "record_shape": {
            "hierarchy": ["requirement", "objective"],
            "determination_rule": "records_without_children",
        },
        "field_authority": FIELD_AUTHORITY,
        "counts": {
            "domains": len(domains),
            "requirements": sum(1 for r in records if r["record_type"] == "requirement"),
            "objectives": sum(1 for r in records if r["record_type"] == "objective"),
            "by_domain": {
                code: sum(1 for r in records if r["domain_code"] == code and r["record_type"] == "requirement")
                for code in domain_order
            },
        },
        "content_sha256": content_hash,
        "not_carried": {
            "objective.evidence_examples": (
                "Truncated (at most 8) copy of the requirement-level Examine objects, "
                "which assessment_methods carries in full; "
                f"{len(placeholder_examples)} objectives held only a legacy placeholder."
            ),
            "placeholder_objectives": placeholder_examples,
        },
        "discrepancy_checks": ARTIFACT_CHECKS,
        "discrepancies": discrepancies,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    catalog = build()
    args.out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = catalog["counts"]
    print(
        f"{args.out}: {counts['domains']} domains, {counts['requirements']} requirements, "
        f"{counts['objectives']} objectives, {len(catalog['discrepancies'])} reported discrepancies"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
