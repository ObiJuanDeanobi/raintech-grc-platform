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
from dataclasses import asdict, dataclass, field, replace
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
QUESTION_FOOTNOTE_RE = re.compile(r"(?<=\?)\d{1,3}\b")
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


# Explicit curation for the one approved 164.308(a)(1) volume-review sample.
# The NIST source remains pinned and unchanged. This selects the smallest
# representative set whose answers can affect a determination or evidence
# request; it is not a generic prompt-scoring engine.
SECURITY_SAMPLE_CURATION: dict[str, tuple[str, tuple[str, ...]]] = {
    "Identify All ePHI and Relevant Information Systems": (
        "164.308(a)(1)(ii)(A)",
        (
            "Has all ePHI generated",
            "Have hardware and software that maintains",
            "Is the current configuration",
        ),
    ),
    "Conduct Risk Assessment": (
        "164.308(a)(1)(ii)(A)",
        ("Are there any prior risk assessments", "Is there intelligence available"),
    ),
    "Implement a Risk Management Program": (
        "164.308(a)(1)(ii)(B)",
        (
            "Is executive leadership",
            "Has a risk management program",
            "Do current safeguards ensure",
            "Has the regulated entity used the results",
        ),
    ),
    "Acquire Information Technology (IT) Systems and Services": (
        "164.308(a)(1)(ii)(B)",
        ("Will new security controls", "Has a cost-benefit analysis"),
    ),
    "Develop and Implement a Sanction Policy": (
        "164.308(a)(1)(ii)(C)",
        (
            "Does the regulated entity have existing sanction policies",
            "Is there a formal process in place to address system misuse",
            "Have workforce members been made aware",
            "Has the need and appropriateness of a tiered structure",
        ),
    ),
    "Develop and Deploy the Information System Activity Review Process": (
        "164.308(a)(1)(ii)(D)",
        (
            "Is there a policy that establishes",
            "Are there corresponding procedures",
            "Who is responsible for the overall process",
            "How often will reviews take place",
        ),
    ),
    "Develop Appropriate Standard Operating Procedures": (
        "164.308(a)(1)(ii)(D)",
        ("How will exception reports", "Where will monitoring reports"),
    ),
    "Implement the Information System Activity Review and Audit Process": (
        "164.308(a)(1)(ii)(D)",
        ("What mechanisms will be implemented",),
    ),
}


def clean(text: str) -> str:
    return " ".join((text or "").split())


def strip_footnotes(name: str) -> str:
    """Remove trailing footnote digits from a key activity name."""
    return FOOTNOTE_TAIL_RE.sub("", clean(name)).strip()


def strip_question_footnotes(text: str) -> str:
    """Remove PDF footnote digits attached directly to question marks."""
    return QUESTION_FOOTNOTE_RE.sub("", clean(text))


def route_security_sample(
    prompts: list[Prompt], *, require_complete: bool = False
) -> dict[str, list[Prompt]]:
    """Route and curate the approved 164.308(a)(1) volume-review sample."""
    if require_complete:
        for group, (_, prefixes) in SECURITY_SAMPLE_CURATION.items():
            group_prompts = [
                strip_question_footnotes(prompt.text)
                for prompt in prompts
                if prompt.group == group
            ]
            for prefix in prefixes:
                matches = [text for text in group_prompts if text.startswith(prefix)]
                if len(matches) != 1:
                    raise ValueError(
                        f"Security sample selector {group!r} / {prefix!r} "
                        f"matched {len(matches)} prompts; expected exactly 1"
                    )

    routed = {
        "164.308(a)(1)(ii)(A)": [],
        "164.308(a)(1)(ii)(B)": [],
        "164.308(a)(1)(ii)(C)": [],
        "164.308(a)(1)(ii)(D)": [],
    }
    for prompt in prompts:
        rule = SECURITY_SAMPLE_CURATION.get(prompt.group)
        if rule is None:
            continue
        record_id, prefixes = rule
        text = strip_question_footnotes(prompt.text)
        if not any(text.startswith(prefix) for prefix in prefixes):
            continue
        routed[record_id].append(replace(prompt, text=text))
    return routed


# --------------------------------------------------------------------------
# Security Rule path: NIST SP 800-66r2
# --------------------------------------------------------------------------


# A section heading reads "5.1.1. Security Management Process (§ 164.308(a)(1))".
# The citation group is greedy over balanced (x) parts, so a heading is never
# matched on a truncated prefix of its citation. Matching on a prefix is what
# made every 164.308(a)(N) standard resolve to §5.1.1 and return Security
# Management Process's prompts.
NIST_HEADING_RE = re.compile(
    r"^(5\.\d+\.\d+)\.\s+(.+?)\s+\(§\s*(164\.\d+(?:\([0-9a-zA-Z]+\))*)\)",
    re.M,
)
# Section 5 ends where the back matter begins; the last standard has no
# following heading to bound it.
NIST_BODY_END_RE = re.compile(r"^(?:6\.\s|References\b|Appendix\s+A\b)", re.M)
# The table of contents repeats every heading verbatim in the front matter.
# Only the body occurrences carry the key-activity tables.
NIST_BODY_START_PAGE = 20

# NIST cites a standard by its containing CFR paragraph; the catalog cites the
# record. They diverge wherever the regulation nests the standard one or two
# levels deeper -- NIST's §164.310(a) is the catalog's 164.310(a)(1), and
# §164.308(a)(1) is 164.308(a)(1)(i). These are the suffixes that difference
# can take. Anything beyond them is a genuine mismatch and stays unresolved.
NIST_CITATION_SUFFIXES = ("", "(1)", "(i)", "(1)(i)")

_HEADING_CACHE: dict[int, list[tuple[str, str, str, int]]] = {}


def nist_headings(doc) -> list[tuple[str, str, str, int]]:
    """Every section-5 body heading as (number, title, citation, page).

    Parsed once per document and ordered by page, so each section's page range
    is derived from where the next one starts rather than re-scanned per
    standard.
    """
    cached = _HEADING_CACHE.get(id(doc))
    if cached is not None:
        return cached

    headings: list[tuple[str, str, str, int]] = []
    for pno in range(NIST_BODY_START_PAGE, doc.page_count):
        for match in NIST_HEADING_RE.finditer(doc[pno].get_text()):
            headings.append(
                (match.group(1), clean(match.group(2)), match.group(3), pno)
            )

    _HEADING_CACHE[id(doc)] = headings
    return headings


def nist_body_end(doc) -> int:
    """First page of the back matter, bounding the final standard."""
    last_start = max((page for _, _, _, page in nist_headings(doc)), default=-1)
    for pno in range(last_start + 1, doc.page_count):
        if NIST_BODY_END_RE.search(doc[pno].get_text()):
            return pno
    return doc.page_count


def resolve_nist_citation(nist_citation: str, catalog_citation: str) -> bool:
    """Does a NIST heading citation name this catalog standard?"""
    return any(
        nist_citation + suffix == catalog_citation
        for suffix in NIST_CITATION_SUFFIXES
    )


def nist_section_bounds(doc, citation: str) -> tuple[int, int]:
    """Page range covering one catalog standard's section in 800-66r2.

    Returns (-1, -1) when 800-66r2 documents no section for the standard.
    """
    headings = nist_headings(doc)
    for index, (_, _, nist_citation, page) in enumerate(headings):
        if not resolve_nist_citation(nist_citation, citation):
            continue
        if index + 1 < len(headings):
            end = headings[index + 1][3]
            # A heading can share a page with the tail of the section above it.
            return (page, max(end, page + 1))
        return (page, nist_body_end(doc))
    return (-1, -1)


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
                    question = strip_question_footnotes(question)
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

    # Security Rule path. The source extraction stays intact, while this
    # representative sample is cleaned, curated, and routed to the four
    # determination-bearing implementation specifications for volume review.
    security_std = f"{SAMPLE_SECURITY}(i)"
    nist_prompts, nist_warnings = extract_nist_prompts(SAMPLE_SECURITY)
    if not nist_prompts:
        detail = "; ".join(nist_warnings) or "no NIST prompts were extracted"
        raise RuntimeError(f"Security sample generation cannot continue: {detail}")
    routed_security = route_security_sample(nist_prompts, require_complete=True)
    kept_security_count = sum(len(rows) for rows in routed_security.values())
    warnings.extend(nist_warnings)
    if security_std in records:
        entries.append(
            {
                "record_id": security_std,
                "path": "nist-800-66r2",
                "prompts": [],
            }
        )
    for rid, record in records.items():
        if rid.startswith(SAMPLE_SECURITY) and rid != security_std:
            entries.append(
                {
                    "record_id": rid,
                    "path": "nist-800-66r2",
                    "prompts": [asdict(p) for p in routed_security.get(rid, [])],
                }
            )

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
        "review_summary": {
            "security": {
                "raw_prompt_count": len(nist_prompts),
                "kept_prompt_count": kept_security_count,
                "omitted_prompt_count": len(nist_prompts) - kept_security_count,
            }
        },
        "entries": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true", default=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        data = build_sample()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
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
