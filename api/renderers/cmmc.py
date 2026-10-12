"""Deterministic CMMC Level 2 standard package rendering (GitHub issue #108).

Like the HIPAA renderer, this consumes only the immutable source snapshot.
Components: final assessment report, the approved SSP, POA&M history, and
the evidence index. The package manifest is written by the generation step.
"""

import csv
import io
from typing import Any

from api.renderers.draftmark import DRAFT_BANNER, UNDECIDED
from api.ssp import docx_bytes, paragraph, ssp_docx


def _shown(status: Any, draft: bool) -> str:
    """A status for reading; a draft says so where nothing has been decided."""
    if status in (None, "", "Blank"):
        return UNDECIDED if draft else "Blank"
    return str(status)


def _report(source: dict[str, Any], draft: bool = False) -> bytes:
    cmmc = source["cmmc"]
    score = cmmc["score"]
    records = {r["record_id"]: r for r in source["records"]}
    body = [
        paragraph("CMMC Level 2 Assessment Report", "Title"),
        paragraph(f"{source['profile']['client_name']} · {source['assessment']['project_name']}"),
        paragraph(
            f"Framework {source['framework']['version']} · source snapshot "
            f"{source['snapshot_id']} · template {source['template_version']}"
        ),
        paragraph("Official score", "Heading1"),
        paragraph(
            f"{score['score']} of {score['maximum_score']} under {score['authority']}. "
            f"Scored only from derived requirement status."
            + (" Provisional until every requirement is decided." if draft else "")
        ),
        paragraph("Requirements", "Heading1"),
    ]
    domain = None
    for requirement in cmmc["requirements"]:
        if requirement["domain"] != domain:
            domain = requirement["domain"]
            body.append(paragraph(domain, "Heading2"))
        body.append(
            paragraph(
                f"{requirement['citation']} {requirement['title']} — "
                f"{_shown(requirement['status'], draft)}"
            )
        )
        for objective_id in requirement["objectives"]:
            objective = records[objective_id]
            body.append(
                paragraph(f"  {objective['citation']}: {_shown(objective.get('status'), draft)}")
            )
    body.append(paragraph("Findings", "Heading1"))
    if not cmmc["findings"]:
        body.append(paragraph("No requirement-level findings were opened."))
    for finding in cmmc["findings"]:
        body.append(paragraph(f"{finding['record_id']}: {finding['title']}"))
    return docx_bytes(body, draft)


def _csv(rows: list[list[Any]], draft: bool = False) -> bytes:
    buffer = io.StringIO()
    if draft:
        buffer.write(DRAFT_BANNER + "\n")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _poam_history(source: dict[str, Any], draft: bool = False) -> bytes:
    rows: list[list[Any]] = [
        ["Requirement", "Finding", "POA&M item", "Status", "Closed at", "Closure rationale"]
    ]
    for finding in source["cmmc"]["findings"]:
        for item in finding["poam_items"]:
            rows.append(
                [
                    finding["record_id"],
                    finding["title"],
                    item["title"],
                    item["status"],
                    item.get("closed_at") or "",
                    item.get("closure_rationale") or "",
                ]
            )
        for event in finding["history"]:
            rows.append(
                [
                    finding["record_id"],
                    finding["title"],
                    f"[history] {event['event']}",
                    "; ".join(event["failed_objectives"]),
                    event["created_at"],
                    "",
                ]
            )
    return _csv(rows, draft)


def _evidence_index(source: dict[str, Any], draft: bool = False) -> bytes:
    rows: list[list[Any]] = [["Evidence version", "Artifact", "Version", "SHA-256"]]
    for version in sorted(
        source["evidence_versions"], key=lambda v: (v["artifact_id"], v["version_number"])
    ):
        rows.append(
            [version["id"], version["artifact_id"], version["version_number"], version["sha256"]]
        )
    return _csv(rows, draft)


# --- Gap-assessment package (ticket #146, ADR 0023) ---------------------------------------
#
# Only the verified score appears here. Wording follows ADR 0011: this is a gap
# assessment, never a certification or a statement of readiness for one.

SCOPE_STATEMENT = (
    "This is a gap assessment, not a C3PAO assessment. It reports what was found against "
    "the 110 CMMC Level 2 requirements and their assessment objectives as the assessment "
    "stood when it was issued. It does not certify the organization, and it does not say "
    "the organization is ready for a certification assessment."
)
_RESULTS = {
    "met": "Met (verified)",
    "evidence_pending": "Met, evidence pending (counted as not met)",
    "not_met": "Not Met",
    "pending": "Pending (counted as not met)",
    "not_assessed": "Not yet assessed (counted as not met)",
}


def _gap(source: dict[str, Any]) -> dict[str, Any]:
    return dict(source["cmmc"]["gap"])


def _lines(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Each requirement's score line (it exists for every requirement not verified Met)."""
    return {line["record_id"]: line for line in source["cmmc"]["score"]["deductions"]}


def _state(source: dict[str, Any], requirement_id: str) -> str:
    return str(_gap(source)["requirements"][requirement_id]["state"])


def _eligibility(line: dict[str, Any] | None, state: str = "not_met") -> str:
    """32 CFR 170.21(a)(2) is about requirements scored NOT MET, so only those get an answer."""
    if line is None:
        return ""
    if state != "not_met":
        return "n/a until assessed"
    return "Yes" if line["conditional_poam_allowed"] else "No"


# Why a partial-credit requirement deducts what it does (DoD Assessment Methodology
# v1.2.1, Annex A; 32 CFR 170.24(c)(2)(i)(B)(4)), by recorded implementation level.
_PARTIAL_NOTES = {
    "IA.L2-3.5.3": {
        "partial": "MFA implemented only for remote and privileged users: 3 points, not 5",
        "none": "MFA not implemented for any users: 5 points",
    },
    "SC.L2-3.13.11": {
        "partial": "Encryption employed but not FIPS-validated: 3 points, not 5",
        "none": "Encryption not employed: 5 points",
    },
}


def _scoring_note(source: dict[str, Any], requirement_id: str, state: str) -> str:
    notes = _PARTIAL_NOTES.get(requirement_id)
    if notes is None:
        return ""
    recorded = source["cmmc"]["score"]["partial_implementations"].get(requirement_id)
    if state != "not_met":
        return "Partial credit applies only once assessed Not Met; the full 5 points are deducted"
    if recorded is None:
        return "Implementation level not recorded: the full 5 points are deducted"
    return notes[recorded["implementation"]]


def _by_domain(source: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: list[tuple[str, list[dict[str, Any]]]] = []
    for requirement in source["cmmc"]["requirements"]:
        if not grouped or grouped[-1][0] != requirement["domain"]:
            grouped.append((requirement["domain"], []))
        grouped[-1][1].append(requirement)
    return grouped


def _score_paragraphs(source: dict[str, Any]) -> list[str]:
    score = source["cmmc"]["score"]
    verified = score["verified"]
    body = [
        paragraph("Verified SPRS score", "Heading1"),
        paragraph(f"{verified['value']} (maximum {score['maximum_score']})", "Heading2"),
        paragraph(f"Arithmetic: {verified['arithmetic']}"),
        paragraph(
            "Verified means a requirement counts as Met only when every one of its objectives "
            "is Met and has current mapped evidence or a documented interview or observation. "
            "A Met result still waiting for evidence is counted as not met. No other score is "
            "shown or used in this package."
        ),
        paragraph(f"Method: {score['methodology']}."),
    ]
    if score["partial_inputs_needed"]:
        body.append(
            paragraph(
                "No partial credit is taken for "
                + ", ".join(score["partial_inputs_needed"])
                + " because the level of implementation was not recorded; "
                "the full value is deducted."
            )
        )
    if any(b.startswith("No point value") for b in score["blockers"]):
        body.append(
            paragraph(
                "CA.L2-3.12.4 (system security plan) is not Met. The DoD Assessment Methodology "
                "does not allow an assessment to be completed without an up-to-date SSP, so this "
                "figure is not a complete assessment score."
            )
        )
    return body


def _conditional_paragraphs(source: dict[str, Any]) -> list[str]:
    conditional = source["cmmc"]["score"]["conditional"]
    body = [
        paragraph("32 CFR 170.21 conditional status checks", "Heading1"),
        paragraph(
            "The rule allows a Conditional Level 2 status only when all three checks pass, "
            "on the verified score. Each check is reported here; none of them stops this report."
        ),
    ]
    unassessed = 0
    for check in conditional["checks"]:
        body.append(
            paragraph(
                f"{'PASS' if check['passed'] else 'FAIL'} — {check['source']}: {check['detail']}"
            )
        )
        for item in check.get("items", []):
            if "allowed" in item:
                if item["allowed"]:
                    continue
                if item["state"] in ("not_met", "evidence_pending"):
                    body.append(
                        paragraph(f"  Not eligible: {item['record_id']} — {item['reason']}")
                    )
                else:
                    unassessed += 1
            elif item["state"] != "met":
                body.append(
                    paragraph(f"  Must be verified Met: {item['record_id']} {item['title']}")
                )
    if unassessed:
        body.append(
            paragraph(
                f"  {unassessed} requirements not yet assessed would also not be eligible, "
                "by their point value."
            )
        )
    body.append(
        paragraph(
            "All three checks pass and the assessment is complete."
            if conditional["eligible"]
            else "The three checks are not all passed, or the assessment is not complete."
        )
    )
    return body


def _family_summary(source: dict[str, Any]) -> list[str]:
    body = [paragraph("Results by family", "Heading1")]
    for domain, requirements in _by_domain(source):
        counts: dict[str, int] = {}
        for requirement in requirements:
            state = _state(source, requirement["record_id"])
            counts[state] = counts.get(state, 0) + 1
        parts = [
            f"{counts[key]} {label}"
            for key, label in (
                ("met", "verified Met"),
                ("evidence_pending", "Met, evidence pending"),
                ("not_met", "Not Met"),
                ("pending", "Pending"),
                ("not_assessed", "not yet assessed"),
            )
            if counts.get(key)
        ]
        body.append(paragraph(f"{domain}: {len(requirements)} requirements — {', '.join(parts)}"))
    return body


def _poam_for(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {finding["record_id"]: finding for finding in source["cmmc"]["findings"]}


def _not_met_paragraphs(source: dict[str, Any]) -> list[str]:
    gap, lines, poams = _gap(source), _lines(source), _poam_for(source)
    body = [paragraph("Requirements that are Not Met", "Heading1")]
    found = False
    for domain, requirements in _by_domain(source):
        failed = [r for r in requirements if _state(source, r["record_id"]) == "not_met"]
        if not failed:
            continue
        found = True
        body.append(paragraph(domain, "Heading2"))
        for requirement in failed:
            line = lines[requirement["record_id"]]
            points = "no point value" if line["points"] is None else f"{line['points']} points"
            body.append(
                paragraph(
                    f"{requirement['record_id']} {requirement['title']} — {points}", "Heading3"
                )
            )
            detail = gap["requirements"][requirement["record_id"]]
            for objective in detail["objectives"]:
                if objective["status"] != "Not Met":
                    continue
                body.append(
                    paragraph(f"Failed objective {objective['record_id']}: {objective['text']}")
                )
                if objective["note"]:
                    body.append(paragraph(f"  Notes: {objective['note']}"))
                if objective["interview_observation"]:
                    body.append(
                        paragraph(
                            f"  Interview or observation: {objective['interview_observation']}"
                        )
                    )
            undecided = [
                o["record_id"]
                for o in detail["objectives"]
                if o["status"] not in ("Met", "Not Met")
            ]
            if undecided:
                body.append(paragraph("  Not yet assessed: " + ", ".join(undecided)))
            if detail["note"]:
                body.append(paragraph(f"  Requirement notes: {detail['note']}"))
            verdict = "eligible" if line["conditional_poam_allowed"] else "not eligible"
            body.append(paragraph(f"POA&M under 32 CFR 170.21: {verdict}. {line['poam_reason']}"))
            items = poams.get(requirement["record_id"], {}).get("poam_items", [])
            if not items:
                body.append(paragraph("POA&M item: none yet."))
            for item in items:
                body.append(paragraph(f"POA&M item: {item['title']} — {item['status']}"))
    if not found:
        body.append(paragraph("No requirement is Not Met."))
    return body


def _pending_paragraphs(source: dict[str, Any]) -> list[str]:
    gap = _gap(source)
    pending = [
        r
        for r in source["cmmc"]["requirements"]
        if _state(source, r["record_id"]) == "evidence_pending"
    ]
    body = [
        paragraph("Met, evidence still needed", "Heading1"),
        paragraph(
            "These requirements were recorded as Met, but not every objective has current "
            "evidence or a documented interview or observation. They are counted as not met in "
            "the verified score until it is added."
        ),
    ]
    if not pending:
        body.append(paragraph("None."))
    for requirement in pending:
        lacking = [
            o["record_id"]
            for o in gap["requirements"][requirement["record_id"]]["objectives"]
            if o["status"] == "Met" and o["basis"] is None
        ]
        body.append(
            paragraph(
                f"{requirement['record_id']} {requirement['title']} — needs: {', '.join(lacking)}"
            )
        )
    return body


def _undecided_paragraphs(source: dict[str, Any]) -> list[str]:
    gap = _gap(source)
    body = [paragraph("Not yet assessed", "Heading1")]
    total, left = gap["objectives_total"], gap["objectives_not_assessed"]
    if not left:
        body.append(paragraph(f"All {total} objectives have been assessed."))
        return body
    body.append(
        paragraph(
            f"{left} objectives are not yet assessed. They are counted as not met in the "
            "verified score."
        )
    )
    for _, requirements in _by_domain(source):
        for requirement in requirements:
            undecided = [
                o["record_id"]
                for o in gap["requirements"][requirement["record_id"]]["objectives"]
                if o["status"] not in ("Met", "Not Met")
            ]
            if undecided:
                body.append(paragraph(f"{requirement['record_id']}: {', '.join(undecided)}"))
    return body


def _gap_report(source: dict[str, Any], draft: bool = False) -> bytes:
    gap = _gap(source)
    left, total = gap["objectives_not_assessed"], gap["objectives_total"]
    body = [
        paragraph("CMMC Level 2 Gap Assessment Report", "Title"),
        paragraph(f"{source['profile']['client_name']} · {source['assessment']['project_name']}"),
        paragraph(
            f"Framework {source['framework']['version']} · source snapshot "
            f"{source['snapshot_id']} · template {source['template_version']}"
        ),
        paragraph("Scope of this report", "Heading1"),
        paragraph(SCOPE_STATEMENT),
    ]
    if left:
        # Only a draft can be incomplete: issuing needs every objective decided.
        body.append(paragraph("This assessment is not complete", "Heading1"))
        body.append(
            paragraph(
                f"{left} of {total} objectives not yet assessed. Each one is counted as not met "
                "below, so the score is not overstated by unfinished work."
            )
        )
    body += _score_paragraphs(source)
    body += _conditional_paragraphs(source)
    body += _family_summary(source)
    body += _not_met_paragraphs(source)
    body += _pending_paragraphs(source)
    body += _undecided_paragraphs(source)
    return docx_bytes(body, draft)


def _sprs_worksheet(source: dict[str, Any], draft: bool = False) -> bytes:
    score = source["cmmc"]["score"]
    lines = _lines(source)
    rows: list[list[Any]] = [
        ["CMMC Level 2 verified SPRS worksheet"],
        ["Client", source["profile"]["client_name"]],
        ["Project", source["assessment"]["project_name"]],
        ["Basis", score["methodology"]],
        ["Scope", SCOPE_STATEMENT],
        [
            "Counted as Met",
            "Requirements whose objectives are all Met with current evidence "
            "or a documented interview or observation",
        ],
        ["Assessment complete", _completeness(source)],
        [],
        [
            "Requirement",
            "Title",
            "Family",
            "Result",
            "Points deducted",
            "May be on a POA&M (32 CFR 170.21)",
            "Scoring note",
        ],
    ]
    for requirement in source["cmmc"]["requirements"]:
        line = lines.get(requirement["record_id"])
        state = _state(source, requirement["record_id"])
        points: Any = ""
        if line is not None:
            points = "no value (SSP required)" if line["points"] is None else line["points"]
        rows.append(
            [
                requirement["record_id"],
                requirement["title"],
                requirement["domain"],
                _RESULTS[state],
                points,
                _eligibility(line, state),
                _scoring_note(source, requirement["record_id"], state),
            ]
        )
    rows += [
        [],
        ["Maximum score", score["maximum_score"]],
        ["Verified SPRS score", score["verified"]["value"]],
        ["Arithmetic", score["verified"]["arithmetic"]],
    ]
    return _csv(rows, draft)


def _completeness(source: dict[str, Any]) -> str:
    left = _gap(source)["objectives_not_assessed"]
    if left:
        return f"No: {left} objectives not yet assessed (counted as not met)"
    if not source["cmmc"]["score"]["complete"]:
        return "No: the system security plan requirement is not Met, so the score is incomplete"
    return "Yes: every objective is assessed"


def _gap_poam(source: dict[str, Any], draft: bool = False) -> bytes:
    score = source["cmmc"]["score"]
    lines, poams = _lines(source), _poam_for(source)
    rows: list[list[Any]] = [
        ["CMMC Level 2 POA&M with 32 CFR 170.21 eligibility"],
        ["Verified SPRS score at issue", score["verified"]["value"]],
        [],
        [
            "Requirement",
            "Title",
            "Result",
            "Points",
            "May be on a POA&M",
            "Why",
            "POA&M item",
            "Status",
            "Closed at",
            "Closure rationale",
        ],
    ]
    for requirement in source["cmmc"]["requirements"]:
        record_id = requirement["record_id"]
        line = lines.get(record_id)
        items = poams.get(record_id, {}).get("poam_items", [])
        state = _state(source, record_id)
        if not items and state != "not_met":
            continue
        base = [
            requirement["record_id"],
            requirement["title"],
            _RESULTS[state],
            "" if line is None or line["points"] is None else line["points"],
            _eligibility(line, state),
            "" if line is None or state != "not_met" else line["poam_reason"],
        ]
        if not items:
            rows.append(base + ["No POA&M item yet", "", "", ""])
        for item in items:
            rows.append(
                base
                + [
                    item["title"],
                    item["status"],
                    item.get("closed_at") or "",
                    item.get("closure_rationale") or "",
                ]
            )
    return _csv(rows, draft)


def _gap_package(source: dict[str, Any], draft: bool) -> list[tuple[str, str, bytes]]:
    ssp_document = source["cmmc"]["ssp"]
    ssp_name = (
        "System_Security_Plan.docx"
        if ssp_document.get("approved_at")
        else "System_Security_Plan_DRAFT.docx"
    )
    return [
        ("assessment_report", "CMMC_L2_Gap_Assessment_Report.docx", _gap_report(source, draft)),
        ("sprs_worksheet", "SPRS_Worksheet_Verified.csv", _sprs_worksheet(source, draft)),
        ("poam", "CMMC_POAM.csv", _gap_poam(source, draft)),
        ("ssp", ssp_name, ssp_docx(ssp_document, draft)),
        ("evidence_index", "Evidence_Index.csv", _evidence_index(source, draft)),
    ]


def render_package(source: dict[str, Any], draft: bool = False) -> list[tuple[str, str, bytes]]:
    if source.get("package_type") == "gap_assessment":
        return _gap_package(source, draft)
    cmmc = source["cmmc"]
    return [
        ("assessment_report", "CMMC_L2_Assessment_Report.docx", _report(source, draft)),
        ("ssp", "System_Security_Plan.docx", ssp_docx(cmmc["ssp"], draft)),
        ("poam", "CMMC_POAM_History.csv", _poam_history(source, draft)),
        ("evidence_index", "Evidence_Index.csv", _evidence_index(source, draft)),
    ]
