"""Build the HIPAA walkthrough prompt layer.

Prompts structure the conversation during an assessment. They carry no
status, produce no findings, and never appear in a report as assessable
items. The determination stays on the citable record. See GitHub issue #29.

Two source paths, split by rule, because the rules differ in what they
publish:

Security Rule
    NIST SP 800-66r2 documents each standard in a "key activities,
    descriptions, and sample questions" table. The sample questions are the
    prompts. Published NIST guidance, machine-readable, current.

Privacy and Breach Notification Rules
    These rules enumerate their own checklists. 45 CFR 164.520(b) lists what
    a notice of privacy practices must contain, item by item. Reading a
    client's notice against that list *is* the assessment, so the prompts are
    the rule's own sub-paragraphs, quoted rather than paraphrased. No external
    source is needed and none is used.

The OCR Audit Protocol is deliberately not a source here. It is published
only as a filterable web page, no PDF exists, repeated fetches truncate
inconsistently, and it is stale against the current rule text.

eCFR is controlling. Guidance is secondary; where they disagree the rule
text wins.

Usage:
    python catalog/hipaa_prompts.py --sample --out <path.json>

Standard library, plus PyMuPDF for the one PDF table extraction.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"
SOURCE_DIR = REPO_ROOT / "catalog" / "sources"
SNAPSHOT = "2026-07-01"

NIST_PDF = SOURCE_DIR / "NIST.SP.800-66r2.pdf"
NIST_LABEL = "NIST SP 800-66r2"

# The two standards used to prove the two source paths before the full
# ingest. One from each, because they produce differently shaped prompts.
SAMPLE_SECURITY = "164.308(a)(1)"
SAMPLE_PRIVACY = "164.520"

# A 800-66r2 key activity cell names its implementation specification and
# designation when it has one, e.g. "2. Conduct Risk Assessment / Implementation
# Specification (Required)".
SPEC_MARKER_RE = re.compile(
    r"Implementation Specification\s*\((Required|Addressable)\)", re.I
)
# Footnote markers ride along on the activity name: "Conduct Risk Assessment31 32".
FOOTNOTE_TAIL_RE = re.compile(r"(?<=[a-z)])\d{1,3}(?:\s+\d{1,3})*\s*$")
ACTIVITY_NUM_RE = re.compile(r"^\s*(\d+)\.\s*")
BULLET_SPLIT_RE = re.compile(r"\n?\s*•\s*")


@dataclass
class Prompt:
    """One conversational prompt. Never carries a status."""

    text: str
    source: str
    source_detail: str = ""
    cfr_paragraph: str = ""
    group: str = ""
    designation: str | None = None
    notes: list[str] = field(default_factory=list)


def clean(text: str) -> str:
    return " ".join((text or "").split())


def strip_footnotes(name: str) -> str:
    """Remove trailing footnote digits from a key activity name."""
    return FOOTNOTE_TAIL_RE.sub("", clean(name)).strip()


# --------------------------------------------------------------------------
# Security Rule path: NIST SP 800-66r2
# --------------------------------------------------------------------------


def nist_section_bounds(doc, citation: str) -> tuple[int, int]:
    """Page range covering one standard's section in 800-66r2.

    Section headings look like "5.1.1. Security Management Process
    (§ 164.308(a)(1))". The body heading is the one that matters; contents
    entries repeat the same text early in the document, so the search starts
    past the front matter.
    """
    stem = citation.split("(")[0]
    para = citation[len(stem):]
    heading = re.compile(
        r"^5\.\d+\.\d+\.\s+.+?\(§\s*" + re.escape(stem) + re.escape(para[:4]),
        re.M,
    )
    any_heading = re.compile(r"^5\.\d+\.\d+\.\s+.+?\(§\s*164\.", re.M)

    start = None
    for pno in range(20, doc.page_count):
        if heading.search(doc[pno].get_text()):
            start = pno
            break
    if start is None:
        return (-1, -1)

    end = doc.page_count
    for pno in range(start + 1, doc.page_count):
        text = doc[pno].get_text()
        for m in any_heading.finditer(text):
            if not heading.search(m.group(0)):
                end = pno + 1
                break
        if end != doc.page_count:
            break
    return (start, end)


def extract_nist_prompts(citation: str) -> tuple[list[Prompt], list[str]]:
    """Pull sample questions for one Security Rule standard."""
    try:
        import fitz
    except ImportError:  # pragma: no cover
        return [], ["PyMuPDF is not installed; 800-66r2 prompts were skipped."]

    if not NIST_PDF.exists():
        return [], [f"{NIST_PDF} is missing; pin the source before ingesting."]

    doc = fitz.open(NIST_PDF)
    start, end = nist_section_bounds(doc, citation)
    if start < 0:
        return [], [f"No 800-66r2 section found for {citation}."]

    prompts: list[Prompt] = []
    warnings: list[str] = []

    for pno in range(start, min(end, doc.page_count)):
        for table in doc[pno].find_tables():
            rows = table.extract()
            if not rows:
                continue
            header = " ".join(str(c or "") for c in rows[0])
            if "Sample Questions" not in header:
                continue

            for row in rows[1:]:
                cells = [clean(str(c or "")) for c in row]
                filled = [c for c in cells if c]
                if len(filled) < 2:
                    continue

                activity_raw = filled[0]
                questions_raw = filled[-1]
                if "?" not in questions_raw:
                    continue

                designation = None
                spec = SPEC_MARKER_RE.search(activity_raw)
                if spec:
                    designation = spec.group(1).lower()
                activity = SPEC_MARKER_RE.sub("", activity_raw)
                activity = strip_footnotes(ACTIVITY_NUM_RE.sub("", activity))

                for question in BULLET_SPLIT_RE.split(questions_raw):
                    question = clean(question)
                    if len(question) < 12 or "?" not in question:
                        continue
                    prompts.append(
                        Prompt(
                            text=question,
                            source=NIST_LABEL,
                            source_detail=f"Key activity: {activity}",
                            group=activity,
                            designation=designation,
                        )
                    )

    if not prompts:
        warnings.append(
            f"800-66r2 section for {citation} found but no sample questions parsed."
        )
    return prompts, warnings


# --------------------------------------------------------------------------
# Privacy and Breach path: the regulation's own enumeration
# --------------------------------------------------------------------------


def load_section_paragraphs(subpart: str, section: str) -> list[tuple[str, str, str]]:
    """Return (paragraph_path, label, body) for one section.

    Delegates to the catalog's own walker so prompt citations and record
    citations come from the same code. Reimplementing the walk here is what
    lost the inline-descent handling and put every child of 45 CFR 164.520(b)
    at the wrong depth.
    """
    sys.path.insert(0, str(REPO_ROOT / "catalog"))
    from hipaa_ingest import iter_section_paragraphs  # noqa: E402

    path_file = SOURCE_DIR / f"title-45-part-164-subpart-{subpart}-{SNAPSHOT}.xml"
    root = ET.fromstring(path_file.read_bytes())

    for div in root.iter("DIV8"):
        if div.attrib.get("N") != section:
            continue
        return [
            (paragraph_path, label or "", body)
            for paragraph_path, label, body, _ in iter_section_paragraphs(div)
        ]
    return []


def extract_cfr_prompts(
    record_id: str, subpart: str, max_depth: int = 2
) -> tuple[list[Prompt], list[str]]:
    """Derive prompts from the sub-paragraphs the rule itself enumerates.

    This quotes the regulation rather than paraphrasing it, so every prompt is
    citable to a CFR paragraph. It creates no assessable records: prompts carry
    no status, and the determination stays on the parent record.
    """
    section = record_id.split("(")[0]
    record_path = record_id[len(section):]
    paragraphs = load_section_paragraphs(subpart, section)

    prompts: list[Prompt] = []
    warnings: list[str] = []
    record_depth = record_path.count("(")

    for path, label, body in paragraphs:
        if not path.startswith(record_path) or path == record_path:
            continue
        depth = path.count("(") - record_depth
        if depth < 1 or depth > max_depth:
            continue
        text = clean(body)
        if label and text.startswith(clean(label)):
            text = clean(text[len(clean(label)):])
        if len(text) < 15:
            continue
        heading = clean(label).rstrip(".") if label else ""
        prompts.append(
            Prompt(
                text=text,
                source="45 CFR Part 164",
                source_detail=f"snapshot {SNAPSHOT}",
                cfr_paragraph=f"45 CFR {section}{path}",
                group=heading,
            )
        )

    if not prompts:
        warnings.append(f"No enumerated sub-paragraphs found beneath {record_id}.")
    return prompts, warnings


# --------------------------------------------------------------------------


def build_sample() -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = {r["id"]: r for r in catalog["records"]}
    warnings: list[str] = []
    entries: list[dict] = []

    # Security Rule path. This spike preserves the raw 800-66r2 standard-level
    # extraction so prompt volume can be reviewed. Production routing is
    # settled separately: NIST-labelled key activities route to their
    # implementation specification, while genuinely standard-wide questions
    # remain parent guidance.
    security_std = f"{SAMPLE_SECURITY}(i)"
    nist_prompts, nist_warnings = extract_nist_prompts(SAMPLE_SECURITY)
    warnings.extend(nist_warnings)
    if security_std in records:
        entries.append(
            {
                "record_id": security_std,
                "path": "nist-800-66r2",
                "prompts": [asdict(p) for p in nist_prompts],
            }
        )
    for rid, record in records.items():
        if rid.startswith(SAMPLE_SECURITY) and rid != security_std:
            entries.append({"record_id": rid, "path": "nist-800-66r2", "prompts": []})

    # Privacy Rule path. Prompts come from the rule's own enumeration and
    # attach to the record whose sub-paragraphs they are.
    for rid, record in sorted(records.items()):
        if record["section"] != SAMPLE_PRIVACY:
            continue
        cfr_prompts, cfr_warnings = extract_cfr_prompts(rid, "E")
        warnings.extend(cfr_warnings)
        entries.append(
            {
                "record_id": rid,
                "path": "cfr-enumeration",
                "prompts": [asdict(p) for p in cfr_prompts],
            }
        )

    return {
        "spike": True,
        "purpose": (
            "Two sample standards for GitHub issue #29, one per source path. "
            "Prompts carry no status and produce no findings; the determination "
            "stays on the record."
        ),
        "sources": [
            {
                "id": "nist-800-66r2",
                "label": NIST_LABEL,
                "covers": "Security Rule (45 CFR 164.308-164.316)",
                "note": "Published NIST guidance. Secondary to the rule text.",
            },
            {
                "id": "cfr-enumeration",
                "label": "45 CFR Part 164",
                "covers": "Privacy Rule and Breach Notification Rule",
                "note": (
                    "The rules enumerate their own checklists. Prompts quote the "
                    "regulation and are citable to a paragraph."
                ),
            },
        ],
        "warnings": warnings,
        "entries": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true", default=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    data = build_sample()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    total = sum(len(e["prompts"]) for e in data["entries"])
    print(f"Wrote {args.out}: {len(data['entries'])} records, {total} prompts")
    for entry in data["entries"]:
        print(f"  {entry['record_id']:24} {entry['path']:18} {len(entry['prompts']):3}")
    for warning in data["warnings"]:
        print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
