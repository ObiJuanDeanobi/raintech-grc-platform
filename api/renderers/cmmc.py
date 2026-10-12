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


def render_package(source: dict[str, Any], draft: bool = False) -> list[tuple[str, str, bytes]]:
    cmmc = source["cmmc"]
    return [
        ("assessment_report", "CMMC_L2_Assessment_Report.docx", _report(source, draft)),
        ("ssp", "System_Security_Plan.docx", ssp_docx(cmmc["ssp"], draft)),
        ("poam", "CMMC_POAM_History.csv", _poam_history(source, draft)),
        ("evidence_index", "Evidence_Index.csv", _evidence_index(source, draft)),
    ]
