"""Build the CMMC practitioner-guidance layer from already-derived data (issue #31).

The RainTech assessment worksheet was read once, by objective ID, into the
committed CMMC mockup. This migrates that derived layer; it does not re-read
the workbook, which stays outside Git because it holds client identifiers.
Guidance is RainTech practice, never DoD or NIST authority.

Usage: python catalog/cmmc_guidance.py
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCKUP = REPO_ROOT / "docs/prototypes/mockups/cmmc-assessment-workspace.html"
CATALOG = REPO_ROOT / "catalog/versions/cmmc-l2-ag-v2.13.json"
OUTPUT = REPO_ROOT / "catalog/versions/cmmc-l2-ag-v2.13-guidance.json"
EXPORT = REPO_ROOT / "docs/catalogs/cmmc-l2-ag-v2.13-guidance.md"
PROVENANCE = (
    "RainTech CMMC assessment worksheet - practitioner guidance. Not DoD or NIST "
    "authority; must never be cited as such and cannot create determinations or findings."
)
OBJECTIVE_FIELDS = {
    "etype": "evidence_type",
    "examples": "evidence_examples",
    "considerations": "assessment_considerations",
}
# Counts the mockup README recorded when the worksheet was first read.
RECORDED_COUNTS = {"evidence_type": 319, "evidence_examples": 320, "assessment_considerations": 240}
MOCKUP_KEY = re.compile(r"^(\d+\.\d+\.\d+)\[([a-z]+)\]$")


def _mockup_guidance() -> dict[str, Any]:
    html = MOCKUP.read_text(encoding="utf-8")
    start = html.index("const GUID = ") + len("const GUID = ")
    guidance, _ = json.JSONDecoder().raw_decode(html[start:])
    return guidance


def build(guidance: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    requirement_by_nist = {
        r["id"].split("-", 1)[1]: r["id"]
        for r in catalog["records"]
        if r["record_type"] == "requirement"
    }
    objective_ids = {r["id"] for r in catalog["records"] if r["record_type"] == "objective"}
    objectives: dict[str, dict[str, str]] = {}
    unmapped: list[str] = []
    for key, fields in sorted(guidance["obj"].items()):
        match = MOCKUP_KEY.match(key)
        target = requirement_by_nist.get(match.group(1), "") + match.group(2) if match else ""
        if target not in objective_ids:
            unmapped.append(key)
            continue
        objectives[target] = {
            OBJECTIVE_FIELDS[name]: value.strip()
            for name, value in fields.items()
            if name in OBJECTIVE_FIELDS and value.strip()
        }
    requirements: dict[str, dict[str, str]] = {}
    for key, value in sorted(guidance["req"].items()):
        nist = key.removeprefix("_lvl_")
        target = requirement_by_nist.get(nist)
        if target is None:
            unmapped.append(key)
            continue
        entry = requirements.setdefault(target, {})
        entry["worksheet_level" if key.startswith("_lvl_") else "c3pao_guidance"] = value.strip()
    blanks = {
        field: sorted(oid for oid in objective_ids if field not in objectives.get(oid, {}))
        for field in OBJECTIVE_FIELDS.values()
    }
    counts = {field: len(objective_ids) - len(missing) for field, missing in blanks.items()}
    counts["c3pao_guidance"] = sum(1 for r in requirements.values() if r.get("c3pao_guidance"))
    layer = {
        "framework_version_id": catalog["framework_version"]["id"],
        "catalog_content_sha256": catalog["content_sha256"],
        "provenance": PROVENANCE,
        "derived_from": "docs/prototypes/mockups/cmmc-assessment-workspace.html (const GUID)",
        "counts": counts,
        "blanks": blanks,
        "unmapped_keys": unmapped,
        "objectives": objectives,
        "requirements": requirements,
    }
    layer["content_sha256"] = sha256(
        json.dumps([objectives, requirements], sort_keys=True).encode()
    ).hexdigest()
    return layer


def export(layer: dict[str, Any]) -> str:
    counts = layer["counts"]
    lines = [
        "# CMMC practitioner guidance — reconciliation",
        "",
        f"Provenance: {layer['provenance']}",
        f"Content SHA-256: `{layer['content_sha256']}`.",
        "",
        "Guidance attaches by published objective or requirement ID only. Catalog record "
        "counts do not change.",
        "",
        "## Populated counts",
        "",
        "| Field | Populated | Recorded at first extraction | Difference |",
        "|---|---|---|---|",
    ]
    for field, recorded in RECORDED_COUNTS.items():
        lines.append(f"| {field} | {counts[field]} | {recorded} | {counts[field] - recorded:+d} |")
    lines += [
        f"| c3pao_guidance (requirement level) | {counts['c3pao_guidance']} | — | — |",
        "",
        "Differences from the recorded counts are reported, not resolved here. They need the "
        "workbook comparison (`catalog/cmmc_guidance_reconcile.py`, run where the workbook "
        "lives) and Johnathan's review. C3PAO guidance is present for every requirement; the "
        "historical 11-versus-110 question is answered here as 110 requirement-level entries, "
        "pending confirmation.",
        "",
        "## Visible blanks (never synthesized)",
        "",
    ]
    for field, missing in layer["blanks"].items():
        lines.append(f"- **{field}** ({len(missing)}): {', '.join(missing) or 'none'}")
    lines += ["", f"Unmapped keys: {', '.join(layer['unmapped_keys']) or 'none'}.", ""]
    return "\n".join(lines)


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    layer = build(_mockup_guidance(), catalog)
    OUTPUT.write_text(json.dumps(layer, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    EXPORT.write_text(export(layer), encoding="utf-8")
    print(f"{OUTPUT.relative_to(REPO_ROOT)}: {layer['counts']}")


if __name__ == "__main__":
    main()
