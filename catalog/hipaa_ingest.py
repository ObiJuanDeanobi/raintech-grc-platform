"""Ingest the HIPAA full-program catalog from eCFR Title 45 Part 164.

Produces a versioned catalog of assessable records for the Security Rule
(subpart C), Privacy Rule (subpart E), and Breach Notification Rule
(subpart D).

Scope note. The Security Risk Analysis is a *workflow* area, not a catalog
area. Risk analysis is 45 CFR 164.308(a)(1)(ii)(A) -- one Required
implementation specification inside the Security Management Process
standard -- and is ingested once, as a Security Rule record. See
docs/specification.md.

Structural note. Only what the regulation itself labels becomes a record:
paragraphs marked "Standard:" or "Implementation specification(s)", plus
section-level records where a subpart publishes obligations under no
"Standard:" label at all. No objective layer is invented; 45 CFR Part 164
publishes no such decomposition and inventing one would produce assessable
records that cannot be cited.

Usage:
    python catalog/hipaa_ingest.py --out catalog/versions/<name>.json

Standard library only. No third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

ECFR_API = "https://www.ecfr.gov/api/versioner/v1/full/{snapshot}/title-45.xml?part=164&subpart={subpart}"

# The catalog areas. The SRA is deliberately absent: it is a work area built
# on top of the Security Rule records, not a catalog area of its own.
WORK_AREAS = {
    "C": ("security", "Security Rule"),
    "E": ("privacy", "Privacy Rule"),
    "D": ("breach", "Breach Notification Rule"),
}

# Sections excluded from the catalog, with the reason each is excluded.
# These are surfaced in the catalog and in the readable export so the
# exclusions are reviewable rather than silent.
EXCLUDED_SECTIONS = {
    "164.302": "Applicability. Scoping provision; carries no assessable obligation.",
    "164.304": "Definitions. Defined terms, not obligations.",
    "164.306": (
        "Security standards: General rules. Governs how the other Security Rule "
        "records are assessed -- including the 164.306(d) addressable decision "
        "rule -- rather than stating a discrete assessable obligation. Its "
        "requirements are evaluated through the standards and implementation "
        "specifications it governs."
    ),
    "164.318": "Compliance dates for initial implementation. Historical dates, expired.",
    "164.400": "Applicability. Scoping provision; carries no assessable obligation.",
    "164.402": "Definitions. Defined terms, not obligations.",
    "164.500": "Applicability. Scoping provision; carries no assessable obligation.",
    "164.501": "Definitions. Defined terms, not obligations.",
    "164.534": "Compliance dates for initial implementation. Historical dates, expired.",
    "164.535": "Severability. Construction provision; carries no assessable obligation.",
}

# Appendix A to Subpart C is the Security Standards Matrix -- a summary table
# restating the standards and implementation specifications of 164.308, .310
# and .312. It is not ingested as records, because that would double-count
# every Security Rule record.
#
# It is used instead as an independent control. The matrix is HHS's own
# enumeration, published in the regulation, so it can be diffed against what
# the section text yields. That diff found a real gap: 164.308(b)(1) is a
# standard in the matrix but its paragraph in the section text carries no
# "Standard:" prefix, so a label-driven parser misses it.
#
# Note the matrix covers only the three safeguard sections. It does not cover
# 164.314 or 164.316, so it is a lower bound on the Security Rule, not a
# complete inventory.
APPENDIX_A = "Appendix A to Subpart C of Part 164"
APPENDIX_A_SCOPE = ("164.308", "164.310", "164.312")
EXCLUDED_APPENDICES = {
    APPENDIX_A: (
        "Security Standards: Matrix. A summary restatement of the standards and "
        "implementation specifications in 164.308, .310 and .312. Not ingested "
        "as records -- that would double-count every Security Rule record. It is "
        "used as an independent control on the parse instead."
    )
}

# The matrix omits the (A) designation on this one specification. The section
# text at 164.308(a)(3)(ii)(B) carries it. The section text is controlling.
APPENDIX_A_KNOWN_OMISSIONS = {"Workforce Clearance Procedure"}

STANDARD_RE = re.compile(r"^Standard:\s*(?P<title>.+?)\s*$")
# The regulation writes implementation specifications three different ways.
# All three must be handled or records are silently lost.
#
# 1. Bare header -- "Implementation specifications:" or "...specifications."
#    The lettered children are the records; the header itself is not one.
#    Subpart C only. Note both the colon and the period form occur; matching
#    only the colon form drops every child under 164.308(a)(5)(ii).
SPEC_HEADER_RE = re.compile(r"^Implementation specifications?\s*[.:]?$")
# 2. Designated header -- "Implementation specifications (Required)". The
#    paragraph itself is the record and carries the designation; its children
#    are its body text. Occurs at 164.314(a)(2) and 164.314(b)(2).
SPEC_DESIGNATED_RE = re.compile(
    r"^Implementation specifications?\s*\((?P<designation>Required|Addressable)\)\s*[.:]?$"
)
# 3. Inline -- "Implementation specification: Documentation." The paragraph
#    itself is the record. Used throughout subparts D and E, and three times
#    in subpart C where it carries a designation in the title.
SPEC_INLINE_RE = re.compile(r"^Implementation specifications?:\s*(?P<title>.+?)\s*$")
DESIGNATION_RE = re.compile(r"\((?P<designation>Required|Addressable)\)")
# Leading paragraph designators, e.g. "(a)", "(1)(i)", "(ii)(A)".
DESIGNATOR_RE = re.compile(r"^((?:\([0-9A-Za-z]+\))+)")
SINGLE_DESIGNATOR_RE = re.compile(r"\(([0-9A-Za-z]+)\)")

# The CFR's positional paragraph hierarchy: (a)(1)(i)(A)(1)(i). Depth
# determines the expected designator type, which is what makes an ambiguous
# token like "(i)" -- both a letter and a roman numeral -- resolvable.
LEVEL_TYPES = [
    "alpha_lower",
    "digit",
    "roman_lower",
    "alpha_upper",
    "digit",
    "roman_lower",
]

ROMAN_VALUES = [
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
]


@dataclass
class Record:
    """One assessable record, traceable to a single CFR citation."""

    id: str
    citation: str
    work_area: str
    subpart: str
    section: str
    paragraph: str
    record_type: str  # "standard" | "implementation_specification" | "section"
    parent_id: str | None
    title: str
    text: str
    designation: str | None  # "required" | "addressable" | None
    source: str
    retrieved: str
    notes: list[str] = field(default_factory=list)


def classify(token: str) -> set[str]:
    """Return the possible hierarchy levels a paragraph designator can occupy.

    CFR paragraph designators are ambiguous in isolation: "(i)" is both a
    lowercase letter and a lowercase roman numeral. Both readings are
    returned and disambiguated by sequence position in ``place``.
    """
    kinds: set[str] = set()
    if token.isdigit():
        kinds.add("digit")

    # A letter designator is a single letter. The CFR's convention past (z)
    # is (aa), (bb), but Part 164 never reaches it -- verified against the
    # pinned source, where every multi-character alphabetic designator is a
    # roman numeral. Admitting doubled letters would make "(ii)" ambiguous
    # with a top-level paragraph and pull it out of its true depth.
    letterish = token.isalpha() and len(token) == 1
    if letterish and token.islower():
        kinds.add("alpha_lower")
    if letterish and token.isupper():
        kinds.add("alpha_upper")

    # Roman numerals are recognized only from the enumerated sequence. A
    # permissive "characters drawn from ivxlcdm" test wrongly admits (c),
    # (d), (l) and (m) -- ordinary letter designators -- as roman numerals,
    # which lets a top-level paragraph be placed six levels deep.
    if token.lower() in ROMAN_VALUES:
        if token.islower():
            kinds.add("roman_lower")
        if token.isupper():
            kinds.add("roman_upper")
    return kinds


def successor(previous: str, token: str, kind: str) -> bool:
    """True when ``token`` directly follows ``previous`` at the given level."""
    if kind == "digit":
        return previous.isdigit() and int(token) == int(previous) + 1
    if kind in ("roman_lower", "roman_upper"):
        seq = ROMAN_VALUES
        lo_prev, lo_tok = previous.lower(), token.lower()
        if lo_prev in seq and lo_tok in seq:
            return seq.index(lo_tok) == seq.index(lo_prev) + 1
        return False
    if kind in ("alpha_lower", "alpha_upper"):
        if len(previous) == 1 and len(token) == 1:
            return ord(token.lower()) == ord(previous.lower()) + 1
    return False


def advances(previous: str, token: str, kind: str) -> bool:
    """True when ``token`` comes after ``previous`` at the given level.

    Weaker than ``successor``: it tolerates gaps, which occur wherever the
    published sequence skips a reserved or removed paragraph.
    """
    if kind == "digit":
        return previous.isdigit() and token.isdigit() and int(token) > int(previous)
    if kind in ("roman_lower", "roman_upper"):
        lo_prev, lo_tok = previous.lower(), token.lower()
        if lo_prev in ROMAN_VALUES and lo_tok in ROMAN_VALUES:
            return ROMAN_VALUES.index(lo_tok) > ROMAN_VALUES.index(lo_prev)
        return False
    if kind in ("alpha_lower", "alpha_upper"):
        if len(previous) == len(token):
            return token.lower() > previous.lower()
        return len(token) > len(previous)
    return False


def first_value(token: str, kind: str) -> bool:
    """True when ``token`` is the first designator at its level."""
    return (
        (kind == "digit" and token == "1")
        or (kind == "alpha_lower" and token == "a")
        or (kind == "alpha_upper" and token == "A")
        or (kind == "roman_lower" and token == "i")
        or (kind == "roman_upper" and token == "I")
    )


def place(
    path: list[tuple[str, str]], token: str, next_token: str | None = None
) -> list[tuple[str, str]]:
    """Position ``token`` in the current paragraph path.

    Placement follows the CFR's positional paragraph hierarchy in
    ``LEVEL_TYPES`` rather than trying to infer depth from sequence alone.
    Sequence-only inference breaks on a common pattern: where a parent
    paragraph carries its first child inline -- as 45 CFR 164.504(e)(1) does
    with (i) -- the next paragraph arrives as "(ii)" with no level for it on
    the stack, and a sequence-only rule mistakes it for a sibling of the
    top-level "(e)".

    Candidate depths are those whose expected type matches the token and
    which either already exist on the path or extend it by exactly one.
    Among candidates, a sibling continuation wins, then a descent for a
    first-value token, then the deepest remaining candidate.
    """
    kinds = classify(token)
    candidates = [
        depth
        for depth, expected in enumerate(LEVEL_TYPES)
        if expected in kinds and depth <= len(path)
    ]
    if not candidates:
        kind = next(iter(kinds)) if kinds else "unknown"
        return path + [(kind, token)]

    # "(i)", "(v)" and "(x)" are irreducibly ambiguous: each is both a letter
    # and a roman numeral. Position alone cannot separate 45 CFR 164.514(h)(1)(i)
    # -- a first roman child -- from 45 CFR 164.530(i), a top-level paragraph
    # following (h). The following designator settles it: a roman numeral is
    # followed by its roman successor, a letter is not.
    if "roman_lower" in kinds and "alpha_lower" in kinds and next_token:
        if successor(token, next_token.lower(), "roman_lower"):
            roman_depths = [d for d in candidates if LEVEL_TYPES[d] == "roman_lower"]
            if roman_depths:
                depth = min(roman_depths)
                return path[:depth] + [("roman_lower", token)]

    # A sibling at a level already on the path.
    for depth in sorted(candidates, reverse=True):
        if depth < len(path):
            kind, previous = path[depth]
            if kind in kinds and successor(previous, token, kind):
                return path[:depth] + [(kind, token)]

    # A first child opens the next level down.
    for depth in sorted(candidates, reverse=True):
        if first_value(token, LEVEL_TYPES[depth]):
            return path[:depth] + [(LEVEL_TYPES[depth], token)]

    # Neither a clean sibling nor a first child. Prefer the shallowest level
    # the token can legitimately advance -- a paragraph that resumes an outer
    # level after a deep excursion is far more common than a jump to the
    # deepest possible level. Gaps in the published sequence are ordinary.
    for depth in sorted(candidates):
        if depth < len(path) and advances(path[depth][1], token, LEVEL_TYPES[depth]):
            return path[:depth] + [(LEVEL_TYPES[depth], token)]

    depth = max(candidates)
    return path[:depth] + [(LEVEL_TYPES[depth], token)]


# A paragraph frequently carries its own first child inline rather than in a
# separate <P>, in one of two styles:
#
#   (f) Fundraising communications-(1) Standard: Uses and disclosures ...
#   Implementation specifications: Verification-(i) Conditions on disclosure ...
#
# The inline designator must still be pushed onto the path, or the *next*
# paragraph -- which arrives as a sibling of that inline child -- has no level
# to attach to and is misread as a top-level paragraph. This is what pulled
# 45 CFR 164.514(f)(2) out to "164.514(i)(2)".
#
# The lookbehind guard matters: cross-references such as
# "§ 164.512(f)(1)(ii)(C)" are full of parenthesized designators that are not
# descents. Only a designator at the start of the body, or one directly
# following a dash or a sentence break, is treated as one.
INLINE_DESCENT_RE = re.compile(
    r"(?:^|(?<=[–—-])|(?<=\.\s)|(?<=\. ))\((?P<token>[0-9A-Za-z]{1,5})\)\s"
)


def inline_descent(body: str, label: str | None) -> str | None:
    """Return the inline first-child designator of a paragraph, if any."""
    text = body
    if label and body.startswith(label):
        text = body[len(label):]
    # The label may stop short of the punctuation that follows it, leaving
    # the remainder as " (i) ..." or ". (i) ...". Trim that so the designator
    # is reachable by the start-anchored alternative.
    text = text.lstrip(" .;:")
    # Only look near the start; a designator deep in the body is prose or a
    # cross-reference, not this paragraph's first child.
    window = text[:220]
    match = INLINE_DESCENT_RE.search(window)
    if not match:
        return None
    token = match.group("token")
    return token if classify(token) else None


def parse_appendix_a(payload: bytes) -> dict:
    """Parse the Security Standards Matrix into an independent inventory.

    Returns the standards it declares, keyed by the paragraph citation it
    gives them, plus its named implementation specifications with their
    designations. Rows whose specification cell is only "(R)" designate the
    standard itself and declare no separate specification.
    """
    root = ET.fromstring(payload)
    appendix = next(
        (d for d in root.iter("DIV9") if d.attrib.get("N") == APPENDIX_A), None
    )
    if appendix is None:
        return {"standards": {}, "specifications": []}

    standards: dict[str, str] = {}
    specifications: list[tuple[str, str | None, str | None]] = []
    current: str | None = None

    rows = [
        [" ".join("".join(cell.itertext()).split()) for cell in row]
        for row in appendix.findall(".//TABLE//TR")
    ]
    for row in rows[1:]:
        name, section, spec = (row + ["", "", ""])[:3]
        if name and not section and not spec:
            continue  # group banner, e.g. "Administrative Safeguards"
        if name and section:
            standards[section] = name
            current = section
        if not spec:
            continue
        match = re.search(r"\((R|A)\)\s*$", spec)
        designation = (
            {"R": "required", "A": "addressable"}[match.group(1)] if match else None
        )
        title = re.sub(r"\s*\((R|A)\)\s*$", "", spec).strip()
        if not title:
            continue  # "(R)" alone designates the standard, not a specification
        specifications.append((title, designation, current))

    return {"standards": standards, "specifications": specifications}


def matrix_citation_resolves(citation: str, standard_ids: set[str]) -> bool:
    """True when a matrix citation names a standard the catalog already has.

    Appendix A cites a standard by the paragraph that *contains* it, not by
    the paragraph the standard's text sits on. Where a standard has
    implementation specifications the regulation splits them: the standard
    is at 164.308(a)(1)(i) and its specifications at 164.308(a)(1)(ii), and
    the matrix cites the parent, 164.308(a)(1). Comparing raw citations
    reports every such standard as missing.
    """
    return citation in standard_ids or f"{citation}(i)" in standard_ids


def reconcile_with_appendix_a(
    records: list[Record], payload: bytes, candidates: dict, retrieved: str, source: str
) -> list[Record]:
    """Promote standards the matrix declares but the section text does not label.

    Every Security Rule standard except one is written "Standard: <name>" in
    the section text. 45 CFR 164.308(b)(1) is not, so a label-driven parse
    misses it -- while Appendix A lists it as a standard. Appendix A is
    published regulation, so promoting it invents nothing.
    """
    inventory = parse_appendix_a(payload)
    have = {r.id for r in records if r.record_type == "standard"}
    additions: list[Record] = []

    for citation, name in inventory["standards"].items():
        if matrix_citation_resolves(citation, have):
            continue
        candidate = candidates.get(citation)
        if candidate is None:
            continue
        title, text = candidate
        section = citation.split("(")[0]
        additions.append(
            Record(
                id=citation,
                citation=f"45 CFR {citation}",
                work_area="security",
                subpart="C",
                section=section,
                paragraph=citation[len(section):],
                record_type="standard",
                parent_id=None,
                title=title.rstrip(".").strip(),
                text=text,
                designation=None,
                source=source,
                retrieved=retrieved,
                notes=[
                    "Declared a standard by Appendix A to Subpart C (Security "
                    "Standards: Matrix). The section text titles this paragraph "
                    'without the "Standard:" prefix every other Security Rule '
                    "standard carries, so it is not recoverable from the section "
                    "text alone. Appendix A is published regulation and is the "
                    "authority here."
                ],
            )
        )

    # Specifications under a promoted standard were parented to whatever
    # standard was innermost at the time, or to nothing. Re-parent them.
    for addition in additions:
        prefix = addition.id
        for record in records:
            if record.record_type != "implementation_specification":
                continue
            if record.id.startswith(addition.section) and record.id != addition.id:
                # Same subtree as the promoted standard, e.g. 164.308(b)(3)
                # under 164.308(b)(1).
                branch = addition.paragraph.rsplit("(", 1)[0]
                if branch and record.paragraph.startswith(branch):
                    record.parent_id = prefix

    return additions


def paragraph_text(element: ET.Element) -> str:
    """Flatten a <P> element to plain text with normalized whitespace."""
    return " ".join("".join(element.itertext()).split())


def italic_text(element: ET.Element) -> str | None:
    """Return the <I> label of a paragraph, if it has one.

    eCFR marks the title of a standard or implementation specification in an
    italic element. Its absence means the paragraph is body text.
    """
    italic = element.find("I")
    if italic is None:
        return None
    return " ".join("".join(italic.itertext()).split())


def strip_designators(text: str) -> tuple[str, str]:
    """Split leading paragraph designators off the body text."""
    match = DESIGNATOR_RE.match(text)
    if not match:
        return "", text.strip()
    return match.group(1), text[match.end():].strip()


def fetch_subpart(subpart: str, snapshot: str, cache_dir: Path | None) -> bytes:
    """Fetch one subpart's XML, preferring a cached snapshot when present."""
    if cache_dir is not None:
        cached = cache_dir / f"title-45-part-164-subpart-{subpart}-{snapshot}.xml"
        if cached.exists():
            return cached.read_bytes()

    url = ECFR_API.format(snapshot=snapshot, subpart=subpart)
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read()

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached = cache_dir / f"title-45-part-164-subpart-{subpart}-{snapshot}.xml"
        cached.write_bytes(payload)
    return payload


def parse_subpart(
    payload: bytes, subpart: str, snapshot: str, retrieved: str
) -> tuple[list[Record], list[dict], dict]:
    """Parse one subpart into records, the exclusions applied, and candidates.

    Candidates are titled paragraphs that produced no record. They are kept so
    Appendix A reconciliation can promote one that the matrix declares to be a
    standard.
    """
    candidates: dict[str, tuple[str, str]] = {}
    root = ET.fromstring(payload)
    work_area, area_label = WORK_AREAS[subpart]
    source = f"eCFR Title 45 Part 164 Subpart {subpart} ({area_label}), snapshot {snapshot}"

    records: list[Record] = []
    exclusions: list[dict] = []

    for appendix in root.iter("DIV9"):
        name = appendix.attrib.get("N", "")
        if name in EXCLUDED_APPENDICES:
            exclusions.append(
                {"unit": name, "kind": "appendix", "reason": EXCLUDED_APPENDICES[name]}
            )

    for section_div in root.iter("DIV8"):
        if section_div.attrib.get("TYPE") != "SECTION":
            continue
        section = section_div.attrib.get("N", "")
        head = section_div.find("HEAD")
        heading = " ".join("".join(head.itertext()).split()) if head is not None else ""
        heading = re.sub(r"^§\s*[\d.]+\s*", "", heading).strip().rstrip(".")

        if section in EXCLUDED_SECTIONS:
            exclusions.append(
                {
                    "unit": f"45 CFR {section}",
                    "kind": "section",
                    "heading": heading,
                    "reason": EXCLUDED_SECTIONS[section],
                }
            )
            continue

        section_records = parse_section(
            section_div, section, heading, subpart, work_area, source, retrieved,
            candidates,
        )
        records.extend(section_records)

    return records, exclusions, candidates


def parse_section(
    section_div: ET.Element,
    section: str,
    heading: str,
    subpart: str,
    work_area: str,
    source: str,
    retrieved: str,
    candidates: dict | None = None,
) -> list[Record]:
    """Parse one section's paragraphs into records."""
    if candidates is None:
        candidates = {}
    records: list[Record] = []
    path: list[tuple[str, str]] = []
    # Innermost enclosing standard, held as (scope_depth, id).
    #
    # A standard's scope is its *parent's* subtree, not its own depth. The
    # regulation places the standard at 164.308(a)(1)(i) and the
    # specifications it governs at 164.308(a)(1)(ii) -- siblings, both
    # children of (a)(1). Scoping a standard to its own depth pops it the
    # moment its sibling specification header arrives, orphaning every
    # specification under it.
    standard_stack: list[tuple[int, str]] = []
    spec_header_depth: int | None = None

    paragraphs = list(section_div.iter("P"))
    for index, paragraph in enumerate(paragraphs):
        raw = paragraph_text(paragraph)
        designators, body = strip_designators(raw)

        if designators:
            tokens = SINGLE_DESIGNATOR_RE.findall(designators)
            # The designator opening the *next* paragraph disambiguates an
            # ambiguous trailing token on this one.
            following = None
            if index + 1 < len(paragraphs):
                next_designators, _ = strip_designators(
                    paragraph_text(paragraphs[index + 1])
                )
                next_tokens = SINGLE_DESIGNATOR_RE.findall(next_designators)
                following = next_tokens[0] if next_tokens else None
            for position, token in enumerate(tokens):
                hint = following if position == len(tokens) - 1 else None
                path = place(path, token, hint)

        depth = len(path)
        while standard_stack and standard_stack[-1][0] >= depth:
            standard_stack.pop()
        if spec_header_depth is not None and depth <= spec_header_depth:
            spec_header_depth = None

        label = italic_text(paragraph)

        # A paragraph may carry its own first child inline. Push that
        # designator after this paragraph is recorded at its own path, so the
        # next paragraph -- a sibling of the inline child -- lands correctly.
        descent = inline_descent(body, label)

        if label is None:
            if descent:
                path = place(path, descent)
            continue

        paragraph_path = "".join(f"({token})" for _, token in path)
        citation = f"45 CFR {section}{paragraph_path}"
        record_id = f"{section}{paragraph_path}"

        standard_match = STANDARD_RE.match(label)
        header_match = SPEC_HEADER_RE.match(label)
        designated_match = SPEC_DESIGNATED_RE.match(label)
        inline_match = SPEC_INLINE_RE.match(label)

        if standard_match:
            title = standard_match.group("title").rstrip(".").strip()
            text = body[len(label):].strip() if body.startswith(label) else body
            records.append(
                Record(
                    id=record_id,
                    citation=citation,
                    work_area=work_area,
                    subpart=subpart,
                    section=section,
                    paragraph=paragraph_path,
                    record_type="standard",
                    parent_id=None,
                    title=title,
                    text=text,
                    designation=None,
                    source=source,
                    retrieved=retrieved,
                )
            )
            standard_stack.append((max(depth - 1, 0), record_id))
            if descent:
                path = place(path, descent)
            continue

        if designated_match:
            # "Implementation specifications (Required)" -- the paragraph is
            # itself the record and carries the designation.
            text = body[len(label):].strip() if body.startswith(label) else body
            parent = standard_stack[-1][1] if standard_stack else None
            records.append(
                Record(
                    id=record_id,
                    citation=citation,
                    work_area=work_area,
                    subpart=subpart,
                    section=section,
                    paragraph=paragraph_path,
                    record_type="implementation_specification",
                    parent_id=parent,
                    title="Implementation specifications",
                    text=text.lstrip("-— ").strip(),
                    designation=designated_match.group("designation").lower(),
                    source=source,
                    retrieved=retrieved,
                )
            )
            if descent:
                path = place(path, descent)
            continue

        if header_match:
            # A bare "Implementation specifications:" header. Its lettered
            # children are the records; the header itself is not one.
            spec_header_depth = depth
            if descent:
                path = place(path, descent)
            continue

        if inline_match:
            raw_title = inline_match.group("title")
            designation_match = DESIGNATION_RE.search(raw_title)
            designation = (
                designation_match.group("designation").lower()
                if designation_match
                else None
            )
            title = DESIGNATION_RE.sub("", raw_title).rstrip(". ").strip()
            text = body[len(label):].strip() if body.startswith(label) else body
            parent = standard_stack[-1][1] if standard_stack else None
            records.append(
                Record(
                    id=record_id,
                    citation=citation,
                    work_area=work_area,
                    subpart=subpart,
                    section=section,
                    paragraph=paragraph_path,
                    record_type="implementation_specification",
                    parent_id=parent,
                    title=title,
                    text=text,
                    designation=designation,
                    source=source,
                    retrieved=retrieved,
                )
            )
            if descent:
                path = place(path, descent)
            continue

        if spec_header_depth is not None and depth > spec_header_depth:
            # A lettered child of a bare implementation-specification header.
            designation_match = DESIGNATION_RE.search(label)
            designation = (
                designation_match.group("designation").lower()
                if designation_match
                else None
            )
            title = DESIGNATION_RE.sub("", label).rstrip(". ").strip()
            text = body[len(label):].strip() if body.startswith(label) else body
            parent = standard_stack[-1][1] if standard_stack else None
            records.append(
                Record(
                    id=record_id,
                    citation=citation,
                    work_area=work_area,
                    subpart=subpart,
                    section=section,
                    paragraph=paragraph_path,
                    record_type="implementation_specification",
                    parent_id=parent,
                    title=title,
                    text=text,
                    designation=designation,
                    source=source,
                    retrieved=retrieved,
                )
            )
            if descent:
                path = place(path, descent)
            continue

        # The paragraph is labelled but is neither a standard nor an
        # implementation specification -- an ordinary titled paragraph such as
        # 45 CFR 164.514(f). It produces no record here, but Appendix A may
        # declare it a standard, so keep it as a candidate. Its inline first
        # child still has to reach the path.
        candidates[record_id] = (
            label,
            body[len(label):].strip() if body.startswith(label) else body,
        )
        if descent:
            path = place(path, descent)

    return records


def add_section_records(
    records: list[Record],
    payload: bytes,
    subpart: str,
    work_area: str,
    source: str,
    retrieved: str,
) -> list[Record]:
    """Add section-level records where a section publishes no standard.

    The Breach Notification Rule labels nothing "Standard:". Without a
    section-level record, obligations such as 164.412 (law enforcement delay)
    and 164.414 (burden of proof) would have no assessable record at all, and
    the implementation specifications under 164.404-164.410 would have no
    parent to roll up to.
    """
    root = ET.fromstring(payload)
    by_section: dict[str, list[Record]] = {}
    for record in records:
        by_section.setdefault(record.section, []).append(record)

    additions: list[Record] = []
    for section_div in root.iter("DIV8"):
        if section_div.attrib.get("TYPE") != "SECTION":
            continue
        section = section_div.attrib.get("N", "")
        if section in EXCLUDED_SECTIONS:
            continue

        existing = by_section.get(section, [])
        if any(record.record_type == "standard" for record in existing):
            continue

        head = section_div.find("HEAD")
        heading = " ".join("".join(head.itertext()).split()) if head is not None else ""
        heading = re.sub(r"^§\s*[\d.]+\s*", "", heading).strip().rstrip(".")

        first = section_div.find("P")
        text = paragraph_text(first) if first is not None else ""

        record_id = section
        additions.append(
            Record(
                id=record_id,
                citation=f"45 CFR {section}",
                work_area=work_area,
                subpart=subpart,
                section=section,
                paragraph="",
                record_type="section",
                parent_id=None,
                title=heading,
                text=text,
                designation=None,
                source=source,
                retrieved=retrieved,
                notes=[
                    "Section-level record. This subpart publishes no "
                    '"Standard:" label, so the section is the assessable unit. '
                    "The section is a published, citable unit of the CFR; no "
                    "structure is invented."
                ],
            )
        )
        for record in existing:
            if record.parent_id is None:
                record.parent_id = record_id

    return additions


def build(snapshot: str, retrieved: str, cache_dir: Path | None) -> dict:
    """Build the full catalog across all three catalog areas."""
    records: list[Record] = []
    exclusions: list[dict] = []

    for subpart in ("C", "E", "D"):
        payload = fetch_subpart(subpart, snapshot, cache_dir)
        work_area, area_label = WORK_AREAS[subpart]
        source = (
            f"eCFR Title 45 Part 164 Subpart {subpart} ({area_label}), "
            f"snapshot {snapshot}"
        )
        parsed, parsed_exclusions, candidates = parse_subpart(
            payload, subpart, snapshot, retrieved
        )
        if subpart == "C":
            parsed.extend(
                reconcile_with_appendix_a(
                    parsed, payload, candidates, retrieved, source
                )
            )
        parsed.extend(
            add_section_records(parsed, payload, subpart, work_area, source, retrieved)
        )
        records.extend(parsed)
        exclusions.extend(parsed_exclusions)

    records.sort(key=lambda r: (r.section, r.paragraph))

    counts: dict[str, dict[str, int]] = {}
    for record in records:
        area = counts.setdefault(
            record.work_area,
            {"total": 0, "standard": 0, "implementation_specification": 0,
             "section": 0, "required": 0, "addressable": 0},
        )
        area["total"] += 1
        area[record.record_type] += 1
        if record.designation:
            area[record.designation] += 1

    return {
        "framework": "HIPAA",
        "framework_version": {
            "id": f"hipaa-45cfr164-{snapshot}",
            "authority": "45 CFR Part 164",
            "source": "eCFR versioner API, Title 45 Part 164",
            "snapshot_date": snapshot,
            "retrieved": retrieved,
            # Whether the required/addressable distinction applies is a
            # property of this pinned version, never a hardcoded assumption.
            # The January 2025 Security Rule NPRM would remove the addressable
            # category; if finalized, that is a new catalog version, not a
            # schema migration.
            "uses_addressable": True,
            "addressable_scope": "Subpart C only, per 45 CFR 164.306(d)",
        },
        "catalog_areas": [
            {"id": "security", "label": "Security Rule", "subpart": "C",
             "sections": "45 CFR 164.302-164.318"},
            {"id": "privacy", "label": "Privacy Rule", "subpart": "E",
             "sections": "45 CFR 164.500-164.535"},
            {"id": "breach", "label": "Breach Notification Rule", "subpart": "D",
             "sections": "45 CFR 164.400-164.414"},
        ],
        "work_areas_note": (
            "HIPAA projects present four work areas over three catalog areas. "
            "The Security Risk Analysis is a workflow area built on the "
            "Security Rule records; risk analysis is 45 CFR "
            "164.308(a)(1)(ii)(A) and appears exactly once, as a Security Rule "
            "implementation specification."
        ),
        "counts": counts,
        "exclusions": exclusions,
        "records": [asdict(record) for record in records],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="2026-07-01",
                        help="eCFR snapshot date to pin (YYYY-MM-DD)")
    parser.add_argument("--retrieved", default=date.today().isoformat(),
                        help="Retrieval date recorded on every record")
    parser.add_argument("--out", type=Path, required=True,
                        help="Path to write the catalog JSON")
    parser.add_argument("--cache-dir", type=Path, default=Path("catalog/sources"),
                        help="Directory holding the pinned source XML")
    parser.add_argument("--no-cache", action="store_true",
                        help="Fetch from eCFR and do not read or write the cache")
    args = parser.parse_args(argv)

    cache_dir = None if args.no_cache else args.cache_dir
    catalog = build(args.snapshot, args.retrieved, cache_dir)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    print(f"Wrote {args.out} with {len(catalog['records'])} records.")
    for area, counts in catalog["counts"].items():
        print(
            f"  {area:9} total={counts['total']:3} "
            f"standard={counts['standard']:3} "
            f"spec={counts['implementation_specification']:3} "
            f"section={counts['section']:2} "
            f"required={counts['required']:3} "
            f"addressable={counts['addressable']:3}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
