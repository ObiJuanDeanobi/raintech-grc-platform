"""Render the issue #29 prompt sample as a walkthrough document.

Spike. Two standards, one per source path, so both can be judged before the
full ingest commits to either.

Usage:
    python catalog/spikes/render_prompt_sample.py --out docs/catalogs/<name>.md

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"
SAMPLE = Path(__file__).parent / "prompts-sample.json"

KIND = {
    "standard": "Standard",
    "implementation_specification": "Implementation specification",
    "section": "Section",
}

PATH_INTRO = {
    "nist-800-66r2": (
        "Security Rule path",
        "Prompts are the sample questions NIST publishes for this standard, "
        "grouped by the key activity they belong to. NIST documents the "
        "standard as a whole, so they attach to the standard rather than being "
        "split across its implementation specifications.",
    ),
    "cfr-enumeration": (
        "Privacy Rule path",
        "Prompts are the sub-paragraphs the regulation itself enumerates, "
        "quoted rather than paraphrased. Each carries its own CFR citation, so "
        "a correction can be written against a paragraph.",
    ),
}


def render(catalog: dict, sample: dict) -> str:
    by_id = {r["id"]: r for r in catalog["records"]}
    catalog_record_count = len(catalog["records"])
    lines: list[str] = []
    add = lines.append

    total = sum(len(e["prompts"]) for e in sample["entries"])
    with_prompts = sum(1 for e in sample["entries"] if e["prompts"])
    sampled_record_count = len(sample["entries"])

    add("# Walkthrough prompts — two sample standards")
    add("")
    add("**Spike for GitHub issue #29. Not an approved catalog artefact.**")
    add("")
    add(
        "Two standards, one per source path, because the paths produce "
        "differently shaped prompts and both have to read well."
    )
    add("")

    add("## What to tell me")
    add("")
    add("1. **Does each path read well in the room?** The Security path gives you "
        "questions to ask. The Privacy path gives you requirements to check a "
        "document against. Both are legitimate; both need to work for you.")
    add("2. **Is the volume right?** "
        f"{total} prompts across {with_prompts} records here. Extrapolated over "
        f"{catalog_record_count} records that is several hundred. Structure, or noise?")
    add("3. **Where should Security Rule prompts sit?** NIST documents the "
        "standard as a whole, so they currently attach to the standard — while "
        "the determinations sit on the four implementation specifications "
        "beneath it. Push them down, or leave them at the standard?")
    add("")

    add("## Provenance")
    add("")
    add("| Source | Covers | Standing |")
    add("|---|---|---|")
    for src in sample["sources"]:
        add(f"| {src['label']} | {src['covers']} | {src['note']} |")
    add("")
    add(
        "_Prompts carry no status, produce no findings, and never appear in a "
        "report as assessable items. The determination stays on the record._"
    )
    add("")

    if sample.get("warnings"):
        add("## Extraction warnings")
        add("")
        for warning in sample["warnings"]:
            add(f"- {warning}")
        add("")

    current_path = None
    for entry in sample["entries"]:
        record = by_id.get(entry["record_id"])
        if record is None:
            continue

        if entry["path"] != current_path:
            current_path = entry["path"]
            title, blurb = PATH_INTRO.get(current_path, (current_path, ""))
            add("---")
            add("")
            add(f"# {title}")
            add("")
            add(blurb)
            add("")

        designation = ""
        if record.get("designation"):
            designation = f" — **{record['designation'].capitalize()}**"

        add(f"## {record['citation']}{designation}")
        add("")
        add(f"### {record['title']}")
        add("")
        add(f"_{KIND.get(record['record_type'], record['record_type'])}_")
        add("")
        if record.get("parent_id") and record["parent_id"] in by_id:
            parent = by_id[record["parent_id"]]
            add(f"Under: {parent['citation']} — {parent['title']}")
            add("")

        add("**Regulation text**")
        add("")
        add(f"> {record['text']}")
        add("")

        add("**Determination** — one for this record")
        add("")
        add("`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`")
        add("")

        if not entry["prompts"]:
            add("**Prompts** — none extracted for this record.")
            add("")
            add("---")
            add("")
            continue

        groups: OrderedDict[str, list[dict]] = OrderedDict()
        for prompt in entry["prompts"]:
            groups.setdefault(prompt.get("group") or "", []).append(prompt)

        add(f"**Prompts** — {len(entry['prompts'])}")
        add("")
        for group, items in groups.items():
            if group:
                marker = ""
                if items[0].get("designation"):
                    marker = f" _({items[0]['designation']})_"
                add(f"**{group}**{marker}")
                add("")
            for prompt in items:
                cite = prompt.get("cfr_paragraph")
                suffix = f"  \n  <sub>{cite}</sub>" if cite else ""
                add(f"- [ ] {prompt['text']}{suffix}")
            add("")

        add("---")
        add("")

    add("## If the answer to question 1 is no")
    add("")
    add(
        "Stop. The approach needs rethinking and ingesting "
        f"{catalog_record_count - sampled_record_count} more records would not "
        "have helped."
    )
    add("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(catalog, sample), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
