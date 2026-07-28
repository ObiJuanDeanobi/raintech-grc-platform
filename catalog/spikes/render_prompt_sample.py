"""Render the issue #29 prompt sample as a walkthrough document.

Spike. Throwaway, and deliberately not wired into the catalog build. It exists
to answer one question, on one standard: could a HIPAA assessment be walked
question-by-question with a client the way a CMMC gap analysis already is?

Joins the sample prompt data to the real catalog so the record text, citation
and designation come from the pinned catalog rather than being restated here.

Usage:
    python catalog/spikes/render_prompt_sample.py --out docs/catalogs/<name>.md

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"
SAMPLE = Path(__file__).parent / "prompts-sample-164.308(a)(1).json"


def render(catalog: dict, sample: dict) -> str:
    by_id = {r["id"]: r for r in catalog["records"]}
    source = sample["source"]
    extraction = sample["extraction"]

    lines: list[str] = []
    add = lines.append

    add("# Walkthrough sample — 45 CFR 164.308(a)(1) Security Management Process")
    add("")
    add("**Spike for GitHub issue #29. Not an approved catalog artefact.**")
    add("")
    add(
        "One question to answer while reading this: **could you run this with a "
        "client in the room?** Not whether the wording is perfect — whether the "
        "shape of it works."
    )
    add("")

    add("## How to read it")
    add("")
    add(
        "Each **record** is a citable unit of 45 CFR Part 164 and carries exactly "
        "one determination. That is what ends up in a report and what a finding "
        "attaches to."
    )
    add("")
    add(
        "The **prompts** beneath it are what you actually ask and look at. They "
        "carry no status of their own, produce no findings, and never appear in a "
        "report as assessable items. They exist to structure the conversation — "
        "the job CMMC assessment objectives do for you today."
    )
    add("")
    add(
        "The checkboxes on prompts are working aids for the walkthrough, not "
        "determinations."
    )
    add("")

    add("## Provenance")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Record text and citations | {catalog['framework_version']['source']}, "
        f"snapshot {catalog['framework_version']['snapshot_date']} |")
    add(f"| Prompts | {source['name']}, revision {source['revision']} |")
    add(f"| Prompts retrieved | {source['retrieved']} |")
    add("")
    add(f"_{source['note']}_")
    add("")

    add("## Extraction limitation — read this before judging coverage")
    add("")
    add(f"**Coverage: {extraction['coverage']}.**")
    add("")
    add(extraction["limitation"])
    add("")
    add(
        "The two records without prompts are shown as they are. Judge the model on "
        "the two that are populated; the gaps are an extraction problem, not a "
        "modelling one."
    )
    add("")

    add("---")
    add("")

    for entry in sample["records"]:
        record = by_id.get(entry["record_id"])
        if record is None:
            continue

        designation = ""
        if record.get("designation"):
            designation = f" — **{record['designation'].capitalize()}**"

        add(f"## {record['citation']}{designation}")
        add("")
        add(f"### {record['title']}")
        add("")
        kind = {
            "standard": "Standard",
            "implementation_specification": "Implementation specification",
            "section": "Section",
        }.get(record["record_type"], record["record_type"])
        add(f"_{kind}_")
        add("")
        if record.get("parent_id"):
            parent = by_id.get(record["parent_id"])
            if parent:
                add(f"Under: {parent['citation']} — {parent['title']}")
                add("")

        add("**Regulation text**")
        add("")
        add(f"> {record['text']}")
        add("")

        if entry.get("established_performance_criteria"):
            add("**Established performance criteria** _(OCR Audit Protocol)_")
            add("")
            add(f"> {entry['established_performance_criteria']}")
            add("")

        if entry.get("key_activity"):
            add(f"**Key activity** _(OCR Audit Protocol)_ — {entry['key_activity']}")
            add("")

        add("**Determination** — one for this record")
        add("")
        add("`Blank`  ·  `Met`  ·  `Not Met`  ·  `Pending`  ·  `N/A (rationale required)`")
        add("")

        if entry["prompts"]:
            add("**Walkthrough prompts** _(OCR Audit Protocol — no status of their own)_")
            add("")
            for prompt in entry["prompts"]:
                add(f"- [ ] {prompt}")
            add("")
        else:
            note = entry.get("note", "No prompts available.")
            add(f"**Walkthrough prompts** — none. {note}")
            add("")

        add("---")
        add("")

    add("## What to tell me")
    add("")
    add("1. **Does the shape work?** One determination on the record, prompts "
        "beneath it that structure the conversation.")
    add("2. **Is the prompt volume right?** Risk analysis has five. Across 192 "
        "records this runs to several hundred. Useful structure, or noise?")
    add("3. **Is anything missing** that you would want in front of you at the "
        "moment of determining this record?")
    add("")
    add(
        "If the answer to 1 is no, stop — the approach needs rethinking and "
        "ingesting 191 more records would not have helped."
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
