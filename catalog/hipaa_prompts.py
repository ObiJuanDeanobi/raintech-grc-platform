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
#
# One activity can cover several specifications, and the source marks those
# collectively -- "Implementation Specifications (Both Required)", "(All
# Addressable)". Missing the plural form leaves those specifications with no
# prompts at all, which is how seven of them came to be unrouted.
#
# The parenthesis is load-bearing: 164.308(a)(8) has an activity about
# "Reviewing All Standards and Implementation Specifications of the Security
# Rule", which is prose about the Rule and not a marker.
SPEC_MARKER_RE = re.compile(
    r"Implementation Specifications?\s*\((?:Both\s+|All\s+)?(Required|Addressable)\)",
    re.I,
)
# Footnote markers ride along on the activity name: "Conduct Risk Assessment31 32".
FOOTNOTE_TAIL_RE = re.compile(r"(?<=[a-z)])\d{1,3}(?:\s+\d{1,3})*\s*$")
QUESTION_FOOTNOTE_RE = re.compile(r"(?<=\?)\d{1,3}\b")
ACTIVITY_NUM_RE = re.compile(r"^\s*(\d+)\.\s*")
# A key activity cell can spill onto a further row, and the spill begins with
# the bullet it was wrapped in rather than a numbered activity name. Read as a
# name it produces phantom activities like "• Ensure that there is a list of
# personnel with authority to approve user requests", which then compete for
# routing against the real ones.
BULLET_LEAD_RE = re.compile(r"^\s*[•o]\s+")
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
    # Privacy and Breach presentation role. Approved July 28, 2026: only an
    # assessment_check renders a checkbox. Left None on Security prompts, which
    # are not classified this way.
    role: str | None = None
    role_reason: str = ""
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


# --------------------------------------------------------------------------
# Routing a key activity to the record whose determination it informs
# --------------------------------------------------------------------------

# Words carrying no discriminating power between one implementation
# specification title and another.
TITLE_STOPWORDS = frozenset(
    {
        "a", "an", "and", "andor", "as", "at", "by", "for", "from", "in", "is",
        "of", "or", "that", "the", "to", "with",
    }
)
# NIST paraphrases a specification's title rather than quoting it, and the two
# inflect differently -- "Authorizing Access" against "Access authorization",
# "Documentation is Available" against "Availability". Comparing a fixed-length
# prefix is crude, but it is transparent, it is testable, and every pairing it
# produces is committed to a reviewable artifact rather than trusted silently.
STEM_LENGTH = 5
# Every title word present. Strong enough to let one activity name two or three
# specifications, which the source does: "Data Backup Plan and Disaster
# Recovery Plan", "Protection from Malicious Software, Login Monitoring, and
# Password Management".
STRONG_MATCH = 1.0
# Enough shared title words to be the best candidate, used only when a single
# specification outscores the rest. "Isolate Healthcare Clearinghouse
# Functions" reaches this against "Isolating health care clearinghouse
# functions" but not STRONG_MATCH, because the source writes "healthcare" where
# the regulation writes "health care".
WEAK_MATCH = 0.5


def stems(text: str) -> set[str]:
    """Discriminating word stems in a title or activity name.

    Hyphens and slashes are dropped rather than split on, so the source's
    "Login" matches the regulation's "Log-in" and "re-use" matches "reuse".
    """
    flattened = re.sub(r"[-/']", "", (text or "").lower())
    words = re.findall(r"[a-z0-9]+", flattened)
    return {
        word[:STEM_LENGTH]
        for word in words
        if word not in TITLE_STOPWORDS and len(word) > 1
    }


def title_match_score(spec_title: str, activity: str) -> float:
    """How much of a specification's title the activity name accounts for."""
    title_stems = stems(spec_title)
    if not title_stems:
        return 0.0
    return len(title_stems & stems(activity)) / len(title_stems)


def route_activities_to_specs(
    activities: list[str], specs: list[dict], standard_id: str
) -> tuple[dict[str, list[str]], list[str]]:
    """Map each marked key activity to the specification records it names.

    Only activities carrying an "Implementation Specification (Required |
    Addressable)" marker are routed; an unmarked activity addresses the
    standard as a whole and stays on the parent as introductory guidance.

    Returns (activity -> record ids, warnings). Nothing is guessed: an activity
    that cannot be resolved is reported rather than attached to a plausible
    record, because a prompt on the wrong determination is worse than a prompt
    that is missing.
    """
    warnings: list[str] = []
    if not specs:
        return {}, warnings

    routed: dict[str, list[str]] = {}
    spec_ids = [spec["id"] for spec in specs]

    # A standard with one specification needs no title matching, and would not
    # survive it: 164.314(a)(1)'s sole child is titled "Implementation
    # specifications", which shares no vocabulary with any activity naming it.
    if len(specs) == 1:
        return {activity: [spec_ids[0]] for activity in activities}, warnings

    unresolved: list[str] = []
    for activity in activities:
        scores = [
            (title_match_score(spec["title"], activity), spec["id"]) for spec in specs
        ]
        strong = [spec_id for score, spec_id in scores if score >= STRONG_MATCH]
        if strong:
            routed[activity] = strong
            continue

        best = max(scores)
        contenders = [spec_id for score, spec_id in scores if score == best[0]]
        if best[0] >= WEAK_MATCH and len(contenders) == 1:
            routed[activity] = contenders
            continue
        unresolved.append(activity)

    # An activity whose paraphrase shares no vocabulary with its specification
    # -- "Retain Documentation for at Least Six Years" against "Time limit" --
    # is resolvable only when it and one specification are all that remain.
    # Anything less certain is reported.
    covered = {spec_id for ids in routed.values() for spec_id in ids}
    remaining = [spec_id for spec_id in spec_ids if spec_id not in covered]
    if len(unresolved) == 1 and len(remaining) == 1:
        routed[unresolved[0]] = remaining
        unresolved = []
        remaining = []

    for activity in unresolved:
        warnings.append(
            f"{standard_id}: key activity {activity!r} is marked as an "
            "implementation specification but names no specification of this "
            "standard; its questions stay on the parent."
        )
    for spec_id in remaining:
        warnings.append(
            f"{spec_id}: no 800-66r2 key activity routes to this "
            "implementation specification."
        )
    return routed, warnings


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

    routed: dict[str, list[Prompt]] = {
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

# Routing exceptions: an untagged key activity that a practitioner has placed on
# a specific implementation specification.
#
# 800-66r2 tags an activity with "Implementation Specification (Required |
# Addressable)" when it belongs to one, and untagged activities stay on the
# standard as context. The tagging is not consistent, so a few activities that
# plainly belong to one child arrive without a tag.
#
# Matching untagged activities on title was measured and rejected: it agreed
# with a practitioner on only two of three candidates at the strict threshold
# and about a quarter at a looser one, because without a tag there is no signal
# that the activity belongs to any child at all and spurious word overlap wins.
# It fails silently, which is the worst way to be wrong. The matcher is kept as
# a candidate generator, and only a recorded practitioner decision moves a
# question. Each entry names who decided and why.
ROUTING_EXCEPTIONS: dict[tuple[str, str], tuple[str, str]] = {
    (
        "164.308(a)(1)(i)",
        "Implement the Information System Activity Review and Audit Process",
    ): (
        "164.308(a)(1)(ii)(D)",
        "Both questions concern the review process itself, not the standard. "
        "Confirmed by Johnathan on July 30, 2026; the same routing he made in "
        "the original hand-curated sample.",
    ),
}

# Candidates the matcher proposed and a practitioner rejected, kept so the same
# proposal is not re-litigated at the next review.
REJECTED_ROUTING_CANDIDATES: dict[tuple[str, str], str] = {
    (
        "164.316(b)(1)",
        "Draft, Maintain, and Update Required Documentation",
    ): (
        "Matched 'Updates' on the word 'Update' alone. Its questions span all "
        "three children -- validity periods are Time limit, who maintains and "
        "reviews is Availability -- so the activity addresses the standard as a "
        "whole. Rejected by Johnathan on July 30, 2026."
    ),
}

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
    # A marker applies to every question of its activity, including questions
    # extracted from an earlier row of the same activity.
    group_designation: dict[str, str] = {}

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
                # A bullet-led cell is the previous activity's text continuing,
                # not a new activity. Blanking it here routes it through the
                # continuation branch below.
                if BULLET_LEAD_RE.match(activity):
                    activity = ""
                activity = strip_footnotes(ACTIVITY_NUM_RE.sub("", activity))

                # A marker can land in its own row, separated from the activity
                # it belongs to: 164.312(a)(1) splits "Automatic Logoff and
                # Encryption and Decryption" from "Implementation
                # Specifications (Both Addressable)". Without rejoining them
                # the activity looks unmarked and its two specifications go
                # unrouted.
                if not activity and prompts:
                    activity = prompts[-1].group
                if not activity:
                    continue
                if designation:
                    group_designation[activity] = designation

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

    prompts = [
        replace(prompt, designation=group_designation.get(prompt.group))
        for prompt in prompts
    ]

    if not prompts:
        warnings.append(
            f"800-66r2 section for {citation} found but no sample questions parsed."
        )
    return prompts, warnings


def route_security_prompts(
    standard_id: str, records: dict[str, dict], prompts: list[Prompt]
) -> tuple[dict[str, list[Prompt]], list[str]]:
    """Attach a standard's prompts to the records that carry the determination.

    Approved July 28, 2026: questions from a key activity that identifies an
    implementation specification attach to that specification, because the
    determination they inform is made there. Genuinely standard-wide questions
    stay on the parent as introductory guidance.

    A parent with implementation specifications has no editable determination,
    so guidance is all a prompt on it can be. A bare standard carries its own
    determination and every prompt attaches to it.
    """
    specs = [
        record
        for record in records.values()
        if record.get("parent_id") == standard_id
        and record["record_type"] == "implementation_specification"
    ]
    marked = sorted({prompt.group for prompt in prompts if prompt.designation})
    routed_activities, warnings = route_activities_to_specs(
        marked, specs, standard_id
    )

    # Practitioner-recorded exceptions override the tag-driven result, and are
    # the only thing that moves an untagged activity off the standard.
    spec_ids = {spec["id"] for spec in specs}
    for (exception_standard, activity), (record_id, _) in ROUTING_EXCEPTIONS.items():
        if exception_standard != standard_id:
            continue
        if record_id not in spec_ids:
            warnings.append(
                f"{standard_id}: routing exception targets {record_id}, which is "
                "not an implementation specification of this standard."
            )
            continue
        if not any(prompt.group == activity for prompt in prompts):
            warnings.append(
                f"{standard_id}: routing exception names key activity "
                f"{activity!r}, which 800-66r2 no longer publishes here."
            )
            continue
        routed_activities[activity] = [record_id]

    by_id = {spec["id"]: spec for spec in specs}
    routed: dict[str, list[Prompt]] = {standard_id: []}
    for spec in specs:
        routed[spec["id"]] = []
    for prompt in prompts:
        targets = routed_activities.get(prompt.group, [standard_id])
        if len(targets) > 1:
            targets = route_question_within_activity(prompt.text, targets, by_id)
        for record_id in targets:
            routed[record_id].append(prompt)
    return routed, warnings


def route_question_within_activity(
    question: str, spec_ids: list[str], by_id: dict[str, dict]
) -> list[str]:
    """Narrow a collectively-marked activity's question to the specifications
    it actually addresses.

    Where one activity covers several specifications the source still writes
    its questions one specification at a time -- under 164.312(a)(1)'s
    "Automatic Logoff and Encryption and Decryption", three questions ask about
    logoff and five about encryption. Attaching all eight to both records would
    put five irrelevant questions on each determination.

    A question that addresses several of them genuinely, such as "Is there a
    formal, written contingency plan? Does it address disaster recovery and
    data backup?", keeps all the specifications it names.
    """
    scores = [
        (title_match_score(by_id[spec_id]["title"], question), spec_id)
        for spec_id in spec_ids
    ]
    strong = [spec_id for score, spec_id in scores if score >= STRONG_MATCH]
    if strong:
        return strong

    best = max(score for score, _ in scores)
    contenders = [spec_id for score, spec_id in scores if score == best]
    if best >= WEAK_MATCH and len(contenders) == 1:
        return contenders
    # Undecidable at the question level; the activity's own reading stands.
    return spec_ids


# --------------------------------------------------------------------------
# Privacy and Breach path: the regulation's own enumeration
# --------------------------------------------------------------------------

# Presentation roles, approved July 28, 2026. Only ASSESSMENT_CHECK renders a
# checkbox; none of the three carries status, produces a finding, or becomes a
# separate assessment result.
ASSESSMENT_CHECK = "assessment_check"
APPLICABILITY_NOTE = "applicability_note"
CONTEXT = "context"

# An exception, exemption, "not required" provision, or scope/N/A condition.
# These support the scope or N/A decision rather than being checked off. A
# prohibition ("may not", "may only") is deliberately absent: it is an
# operative requirement the entity must observe, so it stays a check.
#
# The phrases are anchored so that quoted legal prose, which mentions "may" and
# "not required" constantly in passing, does not demote an operative item.
APPLICABILITY_RE = re.compile(
    r"\b(?:"
    r"does not (?:have a right|apply|include)"
    r"|do(?:es)? not apply"
    r"|(?:is|are|were) not required to\b"
    r"|(?:is|are) not valid"
    r"|(?:is|are) not effective"
    r"|no longer (?:apply|effective|required|valid)"
    r"|not subject to\b"
    r")",
    re.I,
)
# A label that names an exception or a defective/void condition outright. This
# is the strongest and least ambiguous applicability signal.
APPLICABILITY_LABEL_RE = re.compile(
    r"^(?:exception|defective|inapplicab|not applicable)",
    re.I,
)
# An operative obligation, absolute or conditional. "may not"/"may only" are
# prohibitions and count. Conditional obligations ("if X, the entity must Y")
# stay checks per the July 28 decision.
OBLIGATION_RE = re.compile(
    r"\b(?:must|shall|is required|are required|required by law|required to"
    r"|may not|may only|must not|is prohibited)\b",
    re.I,
)
# A genuinely optional element, not merely a sentence containing "may". These
# are the forms the rule uses to mark something a covered entity is free to
# omit: an "Optional elements" label, or "may contain ... in addition to" the
# required content.
OPTIONAL_LABEL_RE = re.compile(r"^optional\b", re.I)
OPTIONAL_BODY_RE = re.compile(
    r"\bmay (?:contain|include).{0,40}\bin addition to\b"
    r"|\bat (?:its|their|the [a-z ]+?'s) option\b"
    r"|\bis optional\b",
    re.I,
)


def _operative_body(label: str, body: str) -> str:
    """Body with a leading repeated label stripped, as the prompts use it."""
    text = clean(body)
    lead = clean(label).rstrip(".")
    if lead and text.lower().startswith(lead.lower()):
        text = clean(text[len(lead):]).lstrip("—-:. ")
    return text


def classify_privacy_paragraphs(
    paragraphs: list[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    """Assign each child paragraph a presentation role and the reason for it.

    Returned aligned to the input, one (role, reason) per paragraph, because
    the same CFR path can appear more than once -- a labelled lead-in and the
    quoted text beneath it share a path -- and a path-keyed result would
    collapse them.

    The ordering encodes a deliberate precedence: structure dominates lexical
    noise. Quoted regulatory prose is dense with "may" and "not required" that
    does not make an item optional, so an enumerated element beneath a
    "must contain:" lead-in stays a check unless it is itself an explicit
    exception. Only an "Optional elements" label, an "in addition to the
    required" permission, or an ancestor that is itself an exception moves an
    item off the checklist. Conditional obligations remain checks, per the
    July 28 decision.

    Nothing here decides an assessment; a role only governs whether a checkbox
    is drawn. The full result is rendered for practitioner review.
    """
    paths = [path for path, _, _ in paragraphs]
    child_count = {
        path: sum(1 for other in paths if other != path and other.startswith(path))
        for path in set(paths)
    }

    # A lead-in imposes an obligation on its enumerated children when its own
    # text carries an obligation word and ends by introducing them.
    obligation_leadins: set[str] = set()
    applicability_ancestors: set[str] = set()

    results: list[tuple[str, str]] = []
    for path, label, body in paragraphs:
        operative = _operative_body(label, body)
        probe = f"{clean(label)} {operative}".strip()
        under_applicability = any(
            path.startswith(a) and path != a for a in applicability_ancestors
        )
        under_obligation = any(
            path.startswith(p) and path != p for p in obligation_leadins
        )

        # 1. Explicit exception, on this item or inherited from an ancestor.
        if APPLICABILITY_LABEL_RE.search(clean(label)) or APPLICABILITY_RE.search(probe):
            role, reason = APPLICABILITY_NOTE, "exception or scope/applicability language"
            applicability_ancestors.add(path)
        elif under_applicability and not OBLIGATION_RE.search(probe):
            role, reason = APPLICABILITY_NOTE, "inherited from an applicability parent"
        # 2. A structural lead-in to enumerated children.
        elif child_count.get(path) and (not operative or operative.endswith(":")):
            role, reason = CONTEXT, "structural lead-in to enumerated children"
            if OBLIGATION_RE.search(probe):
                obligation_leadins.add(path)
        # 3. A genuinely optional element.
        elif OPTIONAL_LABEL_RE.search(clean(label)) or OPTIONAL_BODY_RE.search(probe):
            role, reason = CONTEXT, "optional element"
        # 4. An operative obligation of its own.
        elif OBLIGATION_RE.search(probe):
            role, reason = ASSESSMENT_CHECK, "operative obligation"
        # 5. An enumerated item beneath a "must contain:" lead-in: the
        #    obligation sits on the parent, the item is the thing checked.
        elif under_obligation:
            role, reason = ASSESSMENT_CHECK, "enumerated item under an obligation lead-in"
        # 6. Nothing structural to lean on. A bare standalone permission is
        #    guidance; anything else is left as a check to be reviewed down
        #    rather than silently hidden.
        elif re.search(r"\bmay\b", probe, re.I):
            role, reason = CONTEXT, "standalone permission"
        else:
            role, reason = ASSESSMENT_CHECK, "operative requirement (default)"

        results.append((role, reason))
    return results



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


def build_privacy_classification() -> tuple[dict, list[str]]:
    """Classify every enumerated child paragraph beneath Privacy and Breach
    records into its presentation role.

    Walks at full depth so the leaf items -- the actual checklist -- are
    classified, not only the top two levels the sample used.
    """
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = [
        record
        for record in catalog["records"]
        if record["work_area"] in ("privacy", "breach")
    ]
    subpart = {"privacy": "E", "breach": "D"}

    classified: dict[str, dict] = {}
    warnings: list[str] = []
    seen_sections: dict[str, list[tuple[str, str, str]]] = {}

    for record in sorted(records, key=lambda r: r["id"]):
        section = record["section"]
        sub = subpart[record["work_area"]]
        cache_key = f"{sub}:{section}"
        if cache_key not in seen_sections:
            seen_sections[cache_key] = load_section_paragraphs(sub, section)
        paragraphs = seen_sections[cache_key]

        record_path = record["id"][len(section):]
        children = [
            (path, label, body)
            for path, label, body in paragraphs
            if path.startswith(record_path) and path != record_path
        ]
        if not children:
            continue
        roles = classify_privacy_paragraphs(children)

        entries = []
        for (path, label, body), (role, reason) in zip(children, roles):
            text = clean(body)
            lead = clean(label).rstrip(".")
            if lead and text.lower().startswith(lead.lower()):
                text = clean(text[len(lead):]).lstrip("—-:. ") or clean(body)
            entries.append(
                {
                    "cfr_paragraph": f"45 CFR {section}{path}",
                    "label": clean(label),
                    "text": text,
                    "role": role,
                    "role_reason": reason,
                }
            )
        classified[record["id"]] = {
            "work_area": record["work_area"],
            "title": record["title"],
            "entries": entries,
        }

    return classified, warnings


ROLE_LABELS = {
    ASSESSMENT_CHECK: "Assessment check (checkbox)",
    APPLICABILITY_NOTE: "Applicability note (no checkbox)",
    CONTEXT: "Context (no checkbox)",
}


def render_privacy_classification(classified: dict, warnings: list[str]) -> str:
    """A reviewable account of every Privacy and Breach child paragraph and the
    role it was assigned, with the signal that decided it."""
    from collections import Counter

    totals: Counter = Counter()
    para_total = 0
    for entry in classified.values():
        for item in entry["entries"]:
            totals[item["role"]] += 1
            para_total += 1

    lines = [
        "# Privacy and Breach prompt classification",
        "",
        "_Generated by `catalog/hipaa_prompts.py --classification`. "
        "Do not edit by hand._",
        "",
        "Every enumerated child paragraph beneath a Privacy Rule or Breach "
        "Notification Rule record, quoted from the pinned eCFR snapshot and "
        "assigned a presentation role. Approved July 28, 2026:",
        "",
        "- **Assessment check** — an operative `must` / `shall` / conditional "
        "requirement or a prohibition; renders a checkbox.",
        "- **Applicability note** — an exception, exemption, “not "
        "required” provision, or scope/N/A condition; visible without a "
        "checkbox, supporting the scope or N/A decision.",
        "- **Context** — a structural lead-in or optional permission; guidance "
        "without a checkbox.",
        "",
        "No role carries status, produces a finding, or becomes a separate "
        "assessment result. Text is quoted, not paraphrased.",
        "",
        f"**{len(classified)} records · {para_total} paragraphs · "
        f"{totals[ASSESSMENT_CHECK]} checks · "
        f"{totals[APPLICABILITY_NOTE]} applicability notes · "
        f"{totals[CONTEXT]} context**",
        "",
    ]

    for record_id, entry in classified.items():
        lines.append(f"## 45 CFR {record_id} — {entry['title']}")
        lines.append("")
        lines.append("| Paragraph | Role | Signal | Text |")
        lines.append("|---|---|---|---|")
        for item in entry["entries"]:
            para = item["cfr_paragraph"].replace("45 CFR ", "")
            role = {
                ASSESSMENT_CHECK: "check",
                APPLICABILITY_NOTE: "applicability",
                CONTEXT: "context",
            }[item["role"]]
            text = item["text"].replace("|", "\\|")
            if len(text) > 120:
                text = text[:117] + "…"
            lines.append(
                f"| {para} | {role} | {item['role_reason']} | {text} |"
            )
        lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    return "\n".join(lines)


# Curation under the July 29, 2026 delegation.
#
# The delegation is to keep a prompt when it materially helps determine
# applicability, implementation, or evidence, to remove duplicates and
# administrative noise, and to keep recommendations beyond the CFR only as
# clearly labelled context.
#
# Measured against the corpus, the first clause has almost nothing mechanical
# to act on: 444 routed prompts contain 2 near-duplicate pairs. The 18 prompts
# the approved sample dropped went on topical judgement -- "Has a BIA been
# performed?" is not a CFR requirement, and "Has a training strategy been
# developed?" belongs to 164.308(a)(5). No rule recovers that, and the obvious
# proxy fails immediately: the sample *kept* planning questions such as "How
# will exception reports or logs be reviewed?".
#
# So curation removes only what is demonstrably duplicate, and demotes rather
# than deletes what is demonstrably beyond the CFR. Everything else is retained
# -- the July 29 decision accepted this density -- and the practitioner's marks
# on the rendered walkthrough become an explicit exceptions list, the same
# pattern used for routing promotion. Deleting a citable question on a rule I
# cannot defend is worse than showing it under a heading that says what it is.

# Practices these questions ask about are recommended by 800-66r2 and are not
# required by 45 CFR Part 164. Kept as labelled context so the assessor can use
# them in conversation, never as assessment criteria.
BEYOND_CFR_RE = re.compile(
    r"\b(?:"
    r"business impact analysis|\bBIA\b"
    r"|cost-benefit analysis"
    r"|automated tools?\b"
    r"|external expertise"
    r"|outside (?:vendor|consultant|expertise)"
    r")",
    re.I,
)
# Near-duplicate threshold. Two questions on the same record whose meaningful
# vocabulary overlaps this much are the same question asked twice.
NEAR_DUPLICATE_JACCARD = 0.55


def _content_words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z]+", (text or "").lower())
        if word not in TITLE_STOPWORDS and len(word) > 3
    }


def curate_prompts(prompts: list[Prompt]) -> tuple[list[Prompt], list[str]]:
    """Apply the July 29 curation delegation to one record's prompts.

    Returns (kept, removed-reasons). A prompt is dropped only as a duplicate;
    a prompt recommending practice beyond the CFR is demoted to context rather
    than removed.
    """
    kept: list[Prompt] = []
    removed: list[str] = []
    for prompt in prompts:
        words = _content_words(prompt.text)
        duplicate = False
        for existing in kept:
            other = _content_words(existing.text)
            if not words or not other:
                continue
            overlap = len(words & other) / len(words | other)
            if overlap >= NEAR_DUPLICATE_JACCARD:
                duplicate = True
                removed.append(prompt.text)
                break
        if duplicate:
            continue
        if BEYOND_CFR_RE.search(prompt.text):
            kept.append(
                replace(
                    prompt,
                    role=CONTEXT,
                    role_reason="recommended practice beyond the CFR requirement",
                )
            )
        else:
            kept.append(
                replace(
                    prompt,
                    role=ASSESSMENT_CHECK,
                    role_reason="bears on the mapped CFR determination",
                )
            )
    return kept, removed


def build_prompt_layer() -> dict:
    """The full prompt layer for every record in the pinned catalog version.

    One structure covering both source paths: Security prompts routed from
    800-66r2 key activities, Privacy and Breach prompts quoted from the rule's
    own enumeration. Records with no prompts are listed explicitly rather than
    left silently empty.

    Adds a layer; changes no record. The catalog's 194 determinations, their
    citations, and their text are untouched.
    """
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in catalog["records"]}

    entries: dict[str, dict] = {}
    warnings: list[str] = []
    removed_total = 0

    routing, routing_warnings = build_security_routing()
    warnings.extend(routing_warnings)
    for standard_id, entry in routing.items():
        for record_id, prompts in entry["records"].items():
            curated, removed = curate_prompts(prompts)
            removed_total += len(removed)
            entries[record_id] = {
                "path": "nist-800-66r2",
                "prompts": [asdict(prompt) for prompt in curated],
            }

    classified, classify_warnings = build_privacy_classification()
    warnings.extend(classify_warnings)
    for record_id, entry in classified.items():
        entries[record_id] = {
            "path": "cfr-enumeration",
            "prompts": [
                asdict(
                    Prompt(
                        text=item["text"],
                        source="45 CFR Part 164",
                        source_detail=f"snapshot {SNAPSHOT}",
                        cfr_paragraph=item["cfr_paragraph"],
                        group=item["label"],
                        role=item["role"],
                        role_reason=item["role_reason"],
                    )
                )
                for item in entry["entries"]
            ],
        }

    # Acceptance criterion: a record with no prompts is reported and explained,
    # never silently empty. Each reason below is a property of the source, not
    # a gap in extraction.
    without: list[dict] = []
    for record_id, record in records.items():
        entry = entries.get(record_id)
        if entry and entry["prompts"]:
            continue
        if record["work_area"] == "security":
            reason = (
                "every 800-66r2 key activity for this standard identifies an "
                "implementation specification, so all questions route to its "
                "children; this parent's status is derived and it carries no "
                "editable determination"
            )
        else:
            reason = (
                "the rule states this requirement in full without enumerating "
                "sub-paragraphs, so the record text is itself the prompt"
            )
        without.append({"record_id": record_id, "reason": reason})

    entries = {
        record_id: entry for record_id, entry in entries.items() if entry["prompts"]
    }
    prompt_total = sum(len(entry["prompts"]) for entry in entries.values())

    return {
        "framework_version": catalog["framework_version"]["id"],
        "purpose": (
            "Walkthrough prompts beneath each HIPAA catalog record. Prompts "
            "structure the conversation during an assessment. They carry no "
            "status, produce no findings, and never appear in a report as "
            "assessable items; the determination stays on the citable record."
        ),
        "sources": [
            {
                "id": "nist-800-66r2",
                "label": NIST_LABEL,
                "covers": "Security Rule (45 CFR 164.308-164.316)",
                "revision": "Rev. 2, February 2024",
                "note": "Published NIST guidance. Secondary to the rule text.",
            },
            {
                "id": "cfr-enumeration",
                "label": "45 CFR Part 164",
                "covers": "Privacy Rule and Breach Notification Rule",
                "revision": f"eCFR snapshot {SNAPSHOT}",
                "note": (
                    "The rules enumerate their own checklists. Prompts quote "
                    "the regulation and are citable to a paragraph."
                ),
            },
        ],
        "counts": {
            "records_total": len(records),
            "records_with_prompts": len(entries),
            "records_without_prompts": len(without),
            "prompts_total": prompt_total,
            "duplicates_removed": removed_total,
        },
        "records_without_prompts": sorted(
            without, key=lambda item: item["record_id"]
        ),
        "warnings": warnings,
        "entries": entries,
    }


def security_standards(records: dict[str, dict]) -> list[str]:
    return [
        record["id"]
        for record in records.values()
        if record["work_area"] == "security" and record["record_type"] == "standard"
    ]


def build_security_routing() -> tuple[dict, list[str]]:
    """Route every Security Rule standard's prompts across the whole corpus."""
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in catalog["records"]}

    routing: dict[str, dict] = {}
    warnings: list[str] = []
    for standard_id in security_standards(records):
        prompts, extract_warnings = extract_nist_prompts(standard_id)
        warnings.extend(extract_warnings)
        routed, route_warnings = route_security_prompts(standard_id, records, prompts)
        warnings.extend(route_warnings)
        routing[standard_id] = {
            "raw_prompt_count": len(prompts),
            "records": routed,
        }
    return routing, warnings


def render_security_routing(routing: dict, warnings: list[str]) -> str:
    """A reviewable account of where every Security prompt landed and why.

    Committed so the routing can be read by a practitioner rather than trusted
    because a test passed.
    """
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in catalog["records"]}

    total = sum(
        len(prompts)
        for entry in routing.values()
        for prompts in entry["records"].values()
    )
    lines = [
        "# Security Rule prompt routing",
        "",
        "_Generated by `catalog/hipaa_prompts.py --routing`. Do not edit by hand._",
        "",
        "Every NIST SP 800-66r2 sample question for the 22 Security Rule "
        "standards, and the record whose determination it informs.",
        "",
        "A key activity carrying an `Implementation Specification "
        "(Required | Addressable)` marker routes its questions to the "
        "specification it names. An unmarked activity addresses the standard "
        "as a whole, so its questions stay on the parent as introductory "
        "guidance; the parent's status is derived from its children and it "
        "carries no editable determination.",
        "",
        "Prompts carry no status, produce no findings, and never appear in a "
        "report as assessable items.",
        "",
        f"**{len(routing)} standards · {total} routed prompts · "
        f"{len(warnings)} warnings**",
        "",
    ]

    for standard_id, entry in routing.items():
        standard = records[standard_id]
        lines.append(f"## 45 CFR {standard_id} — {standard['title']}")
        lines.append("")
        lines.append(f"_{entry['raw_prompt_count']} questions in 800-66r2._")
        lines.append("")
        lines.append("| Record | Title | Designation | Prompts |")
        lines.append("|---|---|---|---|")
        for record_id, prompts in entry["records"].items():
            record = records[record_id]
            role = (
                "parent guidance"
                if record_id == standard_id and len(entry["records"]) > 1
                else record.get("designation") or "determination"
            )
            lines.append(
                f"| {record_id} | {record['title']} | {role} | {len(prompts)} |"
            )
        lines.append("")
        for record_id, prompts in entry["records"].items():
            if not prompts:
                continue
            lines.append(f"**{record_id}**")
            lines.append("")
            for prompt in prompts:
                lines.append(f"- {prompt.text}  \n  _{prompt.source_detail}_")
            lines.append("")
        lines.append("---")
        lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true", default=True)
    parser.add_argument(
        "--routing",
        action="store_true",
        help="Render Security Rule prompt routing across all 22 standards.",
    )
    parser.add_argument(
        "--classification",
        action="store_true",
        help="Render Privacy and Breach child-paragraph role classification.",
    )
    parser.add_argument(
        "--layer",
        action="store_true",
        help="Build the full prompt layer for every record in the catalog.",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.layer:
        data = build_prompt_layer()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        counts = data["counts"]
        print(
            f"Wrote {args.out}: {counts['records_with_prompts']} of "
            f"{counts['records_total']} records, "
            f"{counts['prompts_total']} prompts, "
            f"{counts['duplicates_removed']} duplicates removed"
        )
        print(f"  {counts['records_without_prompts']} records without prompts")
        for warning in data["warnings"]:
            print(f"  WARNING: {warning}")
        return 0

    if args.classification:
        classified, warnings = build_privacy_classification()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            render_privacy_classification(classified, warnings), encoding="utf-8"
        )
        para_total = sum(len(e["entries"]) for e in classified.values())
        print(f"Wrote {args.out}: {len(classified)} records, {para_total} paragraphs")
        for warning in warnings:
            print(f"  WARNING: {warning}")
        return 0

    if args.routing:
        routing, warnings = build_security_routing()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            render_security_routing(routing, warnings), encoding="utf-8"
        )
        total = sum(
            len(prompts)
            for entry in routing.values()
            for prompts in entry["records"].values()
        )
        print(f"Wrote {args.out}: {len(routing)} standards, {total} prompts")
        for warning in warnings:
            print(f"  WARNING: {warning}")
        return 0

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
