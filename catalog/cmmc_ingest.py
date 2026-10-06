"""Build the versioned CMMC Level 2 catalog from the archived legacy seed.

This migrates already-extracted content (GitHub issue #30); it does not
re-extract the Assessment Guide. Published identifiers are kept exactly. Text
is carried verbatim: anything that looks like an extraction artifact is
reported in the reconciliation export, never silently corrected.

Usage: python catalog/cmmc_ingest.py
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "legacy/evidence-tracker/cmmc_tracker/data/cmmc_l2_seed.json"
VERSION_ID = "cmmc-l2-ag-v2.13"
OUTPUT = REPO_ROOT / "catalog/versions" / f"{VERSION_ID}.json"
EXPORT = REPO_ROOT / "docs/catalogs" / f"{VERSION_ID}.md"
AUTHORITY = "CMMC Assessment Guide Level 2 Version 2.13 (NIST SP 800-171 Rev. 2, SP 800-171A)"
REQUIREMENT_ID = re.compile(r"^[A-Z]{2}\.L2-3\.\d+\.\d+$")
FOOTNOTE = re.compile(r"\]\s?\d{1,3}\b")
CASE_ARTIFACT = re.compile(r"\[[a-z]{2,}\b")
# A running page header ("AC.L2-3.1.1 – Authorized Access Control") captured mid-text.
PAGE_HEADER = re.compile(r"\b[A-Z]{2}\.L2-3\.\d+\.\d+\s+[–-]\s+\w")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build(seed: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Return the catalog and the list of reported (uncorrected) discrepancies."""
    domains = sorted(seed["domains"], key=lambda item: item["sort_order"])
    domain_codes = [item["code"] for item in domains]
    objectives_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for objective in seed["objectives"]:
        objectives_by_requirement.setdefault(objective["requirement_id"], []).append(objective)
    discrepancies: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    requirements = sorted(
        seed["requirements"],
        key=lambda r: (
            domain_codes.index(r["domain_code"]),
            [int(part) for part in r["id"].split("-")[1].split(".")],
        ),
    )
    for requirement in requirements:
        rid = requirement["id"]
        if not REQUIREMENT_ID.match(rid):
            discrepancies.append({"id": rid, "field": "id", "issue": "Unexpected identifier form"})
        nist = rid.split("-", 1)[1]
        for field in ("name", "text", "potential_methods", "discussion", "further_discussion"):
            value = requirement[field]
            if FOOTNOTE.search(value):
                discrepancies.append(
                    {"id": rid, "field": field, "issue": "Contains an extracted footnote marker"}
                )
            if field != "name" and PAGE_HEADER.search(value):
                discrepancies.append(
                    {"id": rid, "field": field, "issue": "Contains a leaked page header"}
                )
            if CASE_ARTIFACT.search(value):
                discrepancies.append(
                    {"id": rid, "field": field, "issue": "Bracketed text is lower-case"}
                )
        records.append(
            {
                "id": rid,
                "citation": f"CMMC {rid} (NIST SP 800-171 Rev. 2 {nist})",
                "work_area": requirement["domain_code"],
                "record_type": "requirement",
                "parent_id": None,
                "title": requirement["name"],
                "text": requirement["text"],
                "designation": None,
                "potential_methods": requirement["potential_methods"],
                "discussion": requirement["discussion"],
                "further_discussion": requirement["further_discussion"],
                "authority": AUTHORITY,
            }
        )
        children = sorted(objectives_by_requirement.get(rid, []), key=lambda o: o["letter"])
        if not children:
            discrepancies.append({"id": rid, "field": "objectives", "issue": "No objectives"})
        for objective in children:
            oid = objective["id"]
            if oid != rid + objective["letter"]:
                discrepancies.append(
                    {"id": oid, "field": "id", "issue": "Does not equal requirement + letter"}
                )
            records.append(
                {
                    "id": oid,
                    "citation": f"NIST SP 800-171A {nist}[{objective['letter']}]",
                    "work_area": requirement["domain_code"],
                    "record_type": "objective",
                    "parent_id": rid,
                    "title": f"{rid}[{objective['letter']}]",
                    "text": objective["text"],
                    "designation": None,
                    "evidence_examples": list(objective["evidence_examples"]),
                    "authority": AUTHORITY,
                }
            )
    orphans = sorted(set(objectives_by_requirement) - {r["id"] for r in requirements})
    for orphan in orphans:
        discrepancies.append(
            {"id": orphan, "field": "requirement_id", "issue": "Orphan objectives"}
        )
    catalog = {
        "framework": "CMMC",
        "framework_version": {
            "id": VERSION_ID,
            "authority": AUTHORITY,
            "source_title": seed["source"]["title"],
            "source_url": seed["source"]["url"],
            "derived_from": "legacy/evidence-tracker/cmmc_tracker/data/cmmc_l2_seed.json",
            "derived_from_commit": "11fbb32",
            "seed_sha256": sha256(_canonical(seed).encode()).hexdigest(),
        },
        "domains": [{"code": d["code"], "name": d["name"]} for d in domains],
        "counts": {
            "domains": len(domains),
            "requirements": len(requirements),
            "objectives": sum(1 for r in records if r["record_type"] == "objective"),
        },
        "records": records,
    }
    catalog["content_sha256"] = sha256(_canonical(records).encode()).hexdigest()
    return catalog, discrepancies


def export(catalog: dict[str, Any], discrepancies: list[dict[str, str]]) -> str:
    counts = catalog["counts"]
    lines = [
        f"# CMMC Level 2 catalog — {catalog['framework_version']['id']}",
        "",
        f"Authority: {catalog['framework_version']['authority']}.",
        f"Derived from the archived legacy seed (commit "
        f"`{catalog['framework_version']['derived_from_commit']}`), not re-extracted.",
        f"Content SHA-256: `{catalog['content_sha256']}`.",
        "",
        f"{counts['domains']} domains, {counts['requirements']} requirements, "
        f"{counts['objectives']} assessment objectives. Determinations are recorded per "
        "objective; requirement status derives from its objectives.",
        "",
        "## Reconciliation",
        "",
        "Identifiers are unchanged from the seed. No text was modified. The items below look "
        "like extraction artifacts and are reported for review, not corrected.",
        "",
    ]
    if discrepancies:
        groups: dict[tuple[str, str], list[str]] = {}
        for item in discrepancies:
            groups.setdefault((item["issue"], item["field"]), []).append(item["id"])
        lines += ["| Observation | Field | Count | Records |", "|---|---|---|---|"]
        for (issue, field), ids in sorted(groups.items()):
            lines.append(f"| {issue} | {field} | {len(ids)} | {', '.join(ids)} |")
        lines += [
            "",
            "Footnote markers are the guide's footnote numbers captured after a bracketed "
            "source label (for example `[NIST SP 800-171A] 11`). Lower-case bracketed text "
            "(for example `[cui Data]`) differs from the guide's capitalization. Both are "
            "left as-is pending Johnathan's review. Leaked page headers are the guide's "
            "running header (requirement ID and title) captured inside body text.",
        ]
    else:
        lines.append("None.")
    lines += ["", "## Records", ""]
    for record in catalog["records"]:
        if record["record_type"] == "requirement":
            lines += ["", f"### {record['id']} — {record['title']}", "", record["text"], ""]
        else:
            lines.append(f"- **[{record['id'][-1]}]** {record['text']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    catalog, discrepancies = build(seed)
    OUTPUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    EXPORT.write_text(export(catalog, discrepancies), encoding="utf-8")
    print(f"{OUTPUT.relative_to(REPO_ROOT)}: {catalog['counts']}, {len(discrepancies)} reported")


if __name__ == "__main__":
    main()
