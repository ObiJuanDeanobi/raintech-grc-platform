"""Render a pinned HIPAA catalog as Markdown for practitioner review.

The export exists so the catalog can be read and marked up on paper before
any assessment UI is built. Every record carries a review checkbox, its CFR
citation, and its verbatim regulation text, so a correction can be written
against a citation rather than a row number.

Usage:
    python catalog/hipaa_export.py \
        --catalog catalog/versions/<name>.json \
        --out docs/catalogs/<name>.md

Standard library only. No third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AREA_ORDER = ["security", "privacy", "breach"]

DESIGNATION_LABEL = {
    "required": "**Required**",
    "addressable": "**Addressable**",
    None: "",
}

RECORD_TYPE_LABEL = {
    "standard": "Standard",
    "implementation_specification": "Implementation specification",
    "paragraph": "Paragraph",
    "section": "Section",
}


ROLE_PREFIX = {
    "assessment_check": "[ ] ",
    # An applicability note or context entry never renders a checkbox: it
    # supports the scope or N/A decision, or orients the conversation. Neither
    # is something to tick off.
    "applicability_note": "",
    "context": "",
}
ROLE_SUFFIX = {
    "assessment_check": "",
    "applicability_note": " _(applicability)_",
    "context": " _(context)_",
}


def render(catalog: dict, prompt_layer: dict | None = None) -> str:
    version = catalog["framework_version"]
    prompts_by_record = {
        record_id: entry["prompts"]
        for record_id, entry in (prompt_layer or {}).get("entries", {}).items()
    }
    areas = {area["id"]: area for area in catalog["catalog_areas"]}
    records = catalog["records"]
    by_id = {record["id"]: record for record in records}

    lines: list[str] = []
    add = lines.append

    add(f"# HIPAA catalog — {version['id']}")
    add("")
    add("Draft for practitioner review. Not an approved catalog.")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Authority | {version['authority']} |")
    add(f"| Source | {version['source']} |")
    add(f"| Snapshot pinned | {version['snapshot_date']} |")
    add(f"| Retrieved | {version['retrieved']} |")
    add(f"| Required/Addressable in use | {version['uses_addressable']} |")
    add(f"| Addressable scope | {version['addressable_scope']} |")
    add(f"| Total records | {len(records)} |")
    add("")

    add("## How to review this")
    add("")
    add(
        "Tick a record only when you have checked it against the regulation. "
        "Where a record is wrong, write the correction next to its citation — "
        "the citation is the stable identifier and will not change between "
        "catalog versions."
    )
    add("")
    add("Three things are worth your attention specifically:")
    add("")
    add(
        "1. **Scope.** Are these the right assessable units, or does an area "
        "need splitting or merging?"
    )
    add(
        "2. **Exclusions.** The excluded sections are listed at the end with "
        "the reason each was excluded. Those are judgement calls, not facts."
    )
    add(
        "3. **Unlabelled obligations.** Confirm that the four published "
        "paragraph records at 164.412(a)/(b) and 164.414(a)/(b) remain "
        "independently usable assessment units."
    )
    add("")

    add("## Counts")
    add("")
    add("| Catalog area | Standards | Implementation specifications | Paragraphs | Sections | Required | Addressable | Total |")
    add("|---|---:|---:|---:|---:|---:|---:|---:|")
    for area_id in AREA_ORDER:
        counts = catalog["counts"].get(area_id)
        if not counts:
            continue
        add(
            f"| {areas[area_id]['label']} "
            f"| {counts['standard']} "
            f"| {counts['implementation_specification']} "
            f"| {counts['paragraph']} "
            f"| {counts['section']} "
            f"| {counts['required']} "
            f"| {counts['addressable']} "
            f"| {counts['total']} |"
        )
    add("")
    add(f"_{catalog['work_areas_note']}_")
    add("")

    for area_id in AREA_ORDER:
        area = areas.get(area_id)
        if area is None:
            continue
        area_records = [r for r in records if r["work_area"] == area_id]
        if not area_records:
            continue

        add(f"## {area['label']}")
        add("")
        add(f"{area['sections']} — subpart {area['subpart']}. "
            f"{len(area_records)} records.")
        add("")

        current_section = None
        for record in area_records:
            if record["section"] != current_section:
                current_section = record["section"]
                add(f"### 45 CFR {current_section}")
                add("")

            designation = DESIGNATION_LABEL.get(record["designation"], "")
            kind = RECORD_TYPE_LABEL.get(record["record_type"], record["record_type"])
            heading = f"- [ ] **{record['citation']}** — {record['title']}"
            if designation:
                heading += f" ({designation})"
            add(heading)
            add(f"  - _{kind}_")
            if record["parent_id"] and record["parent_id"] in by_id:
                parent = by_id[record["parent_id"]]
                add(f"  - Under: {parent['citation']} — {parent['title']}")
            add(f"  - {record['text']}")
            for note in record["notes"]:
                add(f"  - Note: {note}")

            # Prompts nest under the record whose determination they inform.
            # They carry no status and are never assessable items themselves;
            # only an assessment check renders a checkbox.
            for prompt in prompts_by_record.get(record["id"], []):
                role = prompt.get("role") or "assessment_check"
                # Every prompt states where it came from: a CFR paragraph for
                # the rule's own enumeration, the source and key activity for
                # NIST guidance.
                citation = prompt.get("cfr_paragraph")
                if not citation:
                    citation = prompt.get("source", "")
                    if prompt.get("source_detail"):
                        citation += f" — {prompt['source_detail']}"
                add(
                    f"    - {ROLE_PREFIX.get(role, '')}{prompt['text']}"
                    f"{ROLE_SUFFIX.get(role, '')}"
                )
                add(f"      - _{citation}_")
            add("")

    add("## Exclusions")
    add("")
    add(
        "These units of Part 164 were deliberately not ingested. Each is a "
        "judgement call and can be overruled during review."
    )
    add("")
    for exclusion in catalog["exclusions"]:
        heading = exclusion["unit"]
        if exclusion.get("heading"):
            heading += f" — {exclusion['heading']}"
        add(f"- [ ] **{heading}**")
        add(f"  - {exclusion['reason']}")
        add("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument(
        "--prompts",
        type=Path,
        help="Optional prompt layer to nest beneath each record.",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    prompt_layer = (
        json.loads(args.prompts.read_text(encoding="utf-8")) if args.prompts else None
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(catalog, prompt_layer), encoding="utf-8")
    print(f"Wrote {args.out} from {args.catalog}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
