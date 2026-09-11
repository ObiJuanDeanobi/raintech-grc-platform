"""Deterministic HIPAA report and POA&M rendering.

The renderer deliberately consumes a plain, immutable source snapshot.  It does
not query the live database, infer framework controls, or mutate assessment
records.  Callers should build the snapshot at the issuance boundary and retain
its canonical hash with the generated artifacts.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import re
import zipfile
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

REPORT_SECTIONS = (
    "Assessment Scope",
    "Assessment Method",
    "Determine Scope",
    "Gather Information",
    "Identify Potential Threats",
    "Assess Current Security Measures",
    "Determine Level of Risk",
    "Identify Remediation Activities",
    "Document Gaps",
    "Findings by Source",
    "Impact Determination",
    "Appendix A Key Terminology",
    "Appendix B Implementation Statements",
    "Appendix C POA&M Summary",
)

OPEN_POAM_COLUMNS = (
    "POA&M ID",
    "Assessment ID",
    "Source Record ID",
    "Control Reference",
    "Requirement Family",
    "Requirement ID",
    "Requirement",
    "Requirement Description",
    "Control Group",
    "Control Description",
    "Finding",
    "Risk Rating",
    "Recommendation",
    "Status",
    "Finding Date",
    "Scheduled Completion Date",
    "Actual Completion Date",
    "Owner / Point of Contact",
    "Milestones",
    "Status Summary",
    "Resources Needed",
    "Comments",
    "Evidence Link",
    "Validation Owner",
    "Validation Date",
    "Closure Basis",
    "Action Link",
    "Risk Link",
    "Package / Snapshot ID",
)

# Backward-compatible public name used by validators and golden tests.
POAM_COLUMNS: tuple[str, ...] = OPEN_POAM_COLUMNS

_TOKEN = re.compile(r"\{\{([^{}]+)\}\}")


def _replace_tokens(xml: str, values: Mapping[str, Any]) -> str:
    """Resolve approved OOXML tokens, including entity-encoded token names."""
    return _TOKEN.sub(
        lambda match: html.escape(
            _none(values.get(html.unescape(match.group(1)), "None recorded")), quote=True
        ),
        xml,
    )


def canonical_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and deep-copy the minimum immutable generation contract."""
    required = {"snapshot_id", "framework", "assessment", "profile", "records", "risks"}
    missing = sorted(required - set(snapshot))
    if missing:
        raise ValueError(f"source snapshot missing required fields: {', '.join(missing)}")
    if not isinstance(snapshot["records"], list) or not isinstance(snapshot["risks"], list):
        raise ValueError("source snapshot records and risks must be lists")
    result = copy.deepcopy(dict(snapshot))
    result["source_sha256"] = snapshot_sha256(result)
    return result


def snapshot_sha256(snapshot: Mapping[str, Any]) -> str:
    """Hash the snapshot without allowing a previously stored hash to self-reference."""
    value = {k: v for k, v in snapshot.items() if k != "source_sha256"}
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _none(value: Any, convention: str = "None recorded") -> str:
    if value is None or value == "" or value == [] or value == {}:
        return convention
    if isinstance(value, list | tuple | set):
        return "; ".join(str(item) for item in value) or convention
    return str(value)


def _records(snapshot: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return assessable records only; framework declarations own this decision."""
    declaration = snapshot.get("framework", {}).get("declarations", {})
    ids = set(declaration.get("determination_record_ids", []))
    records = snapshot["records"]
    if ids:
        return [row for row in records if row.get("record_id", row.get("id")) in ids]
    return [row for row in records if row.get("carries_determination", True)]


def report_values(snapshot: Mapping[str, Any]) -> dict[str, str]:
    """Create the named-field map used by the approved DOCX template."""
    s = canonical_snapshot(snapshot)
    assessment = s["assessment"]
    framework = s["framework"]
    profile = s["profile"]
    records = _records(s)
    statuses = [str(row.get("status", row.get("determination", ""))) for row in records]
    values: dict[str, str] = {
        "client_name": _none(profile.get("client_name")),
        "project_name": _none(assessment.get("project_name")),
        "assessment_start_date": _none(assessment.get("start_date")),
        "assessment_end_date": _none(assessment.get("end_date")),
        "assessment_revision": _none(assessment.get("revision")),
        "profile_snapshot_id": _none(profile.get("snapshot_id")),
        "source_snapshot_id": _none(s.get("snapshot_id")),
        "template_version": _none(s.get("template_version", "hipaa-v2")),
        "framework_title": _none(framework.get("title")),
        "framework_version": _none(framework.get("version", framework.get("id"))),
        "framework_declaration_id": _none(framework.get("declaration_id", framework.get("id"))),
        "assessment_source_sha256": s["source_sha256"],
        "empty_state_none_recorded": "None recorded",
        "met_count": str(statuses.count("Met")),
        "not_met_count": str(statuses.count("Not Met")),
        "not_applicable_count": str(statuses.count("N/A")),
        "assessment_decision": _none(assessment.get("decision")),
        "issuance_decision": _none(assessment.get("issuance_decision")),
    }
    rows = [_joined_record(s, row) for row in _records(s)]

    # Repeated appendix/table fields are newline-delimited so the same approved
    # template remains useful for one or many framework records.
    def joined(key: str, *fallback: str) -> str:
        return (
            "\n".join(
                _none(
                    next(
                        (row.get(k) for k in (key, *fallback) if row.get(k) not in (None, "")), None
                    )
                )
                for row in rows
            )
            or "None recorded"
        )

    values.update(
        {
            "control_reference": joined("citation", "record_id", "id"),
            "framework_record_id": joined("record_id", "id"),
            "objective": joined("objective", "assessment_objective"),
            "designation": joined("designation"),
            "citation": joined("citation", "record_id", "id"),
            "requirement_text": joined("text", "title"),
            "final_determination": joined("status", "determination"),
            "implementation_statement": joined("implementation_statement", "assessor_note"),
            "scope_context": joined("scope_context", "work_area"),
            "evidence_references": joined("evidence_references", "evidence"),
            "finding_id": joined("finding_id"),
            "action_id": joined("corrective_action_id", "action_id"),
            "validation_state": joined("validation_state", "status"),
            "requirement": joined("requirement", "text", "title"),
            "control_group": joined("control_group", "work_area"),
            "control_description": joined("control_description", "text", "title"),
            "poam_id": joined("poam_id", "poa_m_id"),
            "risk_rating": joined("risk_rating", "risk"),
            "poam_status": joined("poam_status", "status"),
            "scheduled_completion_date": joined("scheduled_completion_date"),
            "action_owner": joined("action_owner", "owner"),
            "validation_evidence": joined("validation_evidence"),
            "findings_grouped_by_source": "\n".join(
                f"{_none(r.get('work_area'))}: {_none(r.get('finding_id'))}" for r in rows
            )
            or "None recorded",
            "assessment_scope_narrative": _none(s.get("scope", {}).get("narrative")),
            "impact_determination_narrative": _none(s.get("impact_determination")),
            "poam_summary_and_artifact_reference": _none(s.get("poam_artifact_reference")),
            "sra_scope_summary": _none(s.get("sra", {}).get("scope")),
            "sra_threat_summary": _none(s.get("sra", {}).get("threats")),
            "sra_vulnerability_summary": _none(s.get("sra", {}).get("vulnerabilities")),
            "sra_likelihood_summary": _none(s.get("sra", {}).get("likelihood")),
            "sra_impact_summary": _none(s.get("sra", {}).get("impact")),
            "sra_inherent_risk_summary": _none(s.get("sra", {}).get("inherent_risk")),
            "sra_safeguard_summary": _none(s.get("sra", {}).get("safeguards")),
            "sra_residual_risk_summary": _none(s.get("sra", {}).get("residual_risk")),
            "sra_treatment_summary": _none(s.get("sra", {}).get("treatment")),
            "sra_exclusions_with_rationale": _none(s.get("sra", {}).get("exclusions")),
        }
    )
    # Every remaining approved token is intentionally resolved to a safe empty state.
    return values


def render_report(template_path: Path, output_path: Path, snapshot: Mapping[str, Any]) -> str:
    """Render named fields into a DOCX while preserving the approved package."""
    values = report_values(snapshot)
    source = BytesIO()
    with (
        zipfile.ZipFile(template_path, "r") as zin,
        zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                data = _replace_tokens(data.decode("utf-8"), values).encode("utf-8")
            zout.writestr(item, data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(source.getvalue())
    return snapshot_sha256(snapshot)


def _xlsx_cell(reference: str, value: Any) -> str:
    escaped = html.escape(_none(value), quote=True)
    return f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{escaped}</t></is></c>'


def _excel_column(index: int) -> str:
    """Return a one-based Excel column name (1=A, 27=AA)."""
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _joined_record(snapshot: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    """Join normalized finding/action/risk collections to one framework record."""
    key = row.get("record_id", row.get("id"))
    result = dict(row)
    for collection, aliases in (
        ("findings", ("finding_id", "id")),
        ("actions", ("action_id", "id")),
        ("risks", ("risk_id", "id")),
    ):
        wanted = row.get(aliases[0], row.get(aliases[1]))
        if wanted:
            match = next(
                (
                    item
                    for item in snapshot.get(collection, [])
                    if item.get("id") == wanted or item.get("record_id") == key
                ),
                None,
            )
            if match:
                result.update(match)
    return result


def render_poam(template_path: Path, output_path: Path, snapshot: Mapping[str, Any]) -> str:
    """Populate the approved workbook using inline strings and exact 29-column rows."""
    s = canonical_snapshot(snapshot)
    rows = [
        _joined_record(s, r)
        for r in _records(s)
        if r.get("status", r.get("determination")) == "Not Met"
    ]
    assessment = s.get("assessment", {})
    profile = s.get("profile", {})
    token_values: dict[str, Any] = {
        **report_values(s),
        "assessment_id": assessment.get("id"),
        "client_name": profile.get("client_name"),
        "derived_from_assessment": assessment.get("id"),
        "profile_id": profile.get("snapshot_id", profile.get("id")),
        "project_name": assessment.get("project_name"),
        "scope_summary": s.get("scope", {}).get("narrative"),
        "source_snapshot_id": s.get("snapshot_id"),
        "package_snapshot_id": s.get("snapshot_id"),
    }
    source = BytesIO()
    with (
        zipfile.ZipFile(template_path, "r") as zin,
        zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in {"xl/worksheets/sheet2.xml", "xl/worksheets/sheet4.xml"}:
                xml = data.decode("utf-8")
                match = re.search(
                    r"(<(?:[A-Za-z0-9_]+:)?row r=\"3\".*?</(?:[A-Za-z0-9_]+:)?row>)", xml
                )
                if match:
                    template_row = match.group(1)
                    generated = []
                    for n, row in enumerate(rows, 3):
                        values = [
                            s.get("snapshot_id"),
                            s.get("assessment", {}).get("id"),
                            row.get("record_id"),
                            row.get("citation", row.get("record_id")),
                            row.get("work_area"),
                            row.get("record_id"),
                            row.get("title"),
                            row.get("text"),
                            row.get("control_group", row.get("work_area")),
                            row.get("control_description", row.get("text")),
                            row.get("finding_id"),
                            row.get("risk_rating", row.get("risk")),
                            row.get("recommendation"),
                            row.get("status", "Not Met"),
                            row.get("finding_date"),
                            row.get("scheduled_completion_date"),
                            row.get("actual_completion_date"),
                            row.get("action_owner", row.get("owner")),
                            row.get("milestones"),
                            row.get("status_summary"),
                            row.get("resources"),
                            row.get("comments"),
                            row.get("evidence_link"),
                            row.get("validation_owner"),
                            row.get("validation_date"),
                            row.get("closure_basis"),
                            row.get("action_id"),
                            row.get("risk_id"),
                            s.get("snapshot_id"),
                        ]
                        cells = "".join(
                            _xlsx_cell(f"{_excel_column(i + 1)}{n}", value)
                            for i, value in enumerate(values)
                        )
                        generated.append(f'<row r="{n}">{cells}</row>')
                    xml = xml.replace(template_row, "".join(generated) or template_row)
                data = _replace_tokens(xml, token_values).encode("utf-8")
            elif item.filename.startswith("xl/") and item.filename.endswith(".xml"):
                data = _replace_tokens(data.decode("utf-8"), token_values).encode("utf-8")
            zout.writestr(item, data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(source.getvalue())
    return str(s["source_sha256"])


def render_package_components(
    template_dir: Path, output_dir: Path, snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    """Generate the governed report and POA&M as a single traceable package."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / "HIPAA_Assessment_Report.docx"
    poam = output_dir / "HIPAA_POAM.xlsx"
    source_hash = render_report(
        template_dir / "RainTech_HIPAA_Combined_Assessment_Report_v2.docx", report, snapshot
    )
    render_poam(template_dir / "RainTech_HIPAA_POAM_v2.xlsx", poam, snapshot)
    return {
        "source_snapshot_id": snapshot["snapshot_id"],
        "source_sha256": source_hash,
        "report": report,
        "poam": poam,
    }


def validate_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    """Return deterministic completeness errors; an empty list means renderable."""
    errors: list[str] = []
    try:
        canonical_snapshot(snapshot)
    except ValueError as exc:
        return [str(exc)]
    for index, row in enumerate(_records(snapshot)):
        if not row.get("record_id", row.get("id")):
            errors.append(f"records[{index}] missing record_id")
        status = row.get("status", row.get("determination"))
        if status not in {"Met", "Not Met", "N/A"}:
            errors.append(f"records[{index}] has non-final determination")
        if status == "N/A" and not row.get("rationale"):
            errors.append(f"records[{index}] N/A requires rationale")
        if status == "Not Met" and not row.get("finding_id"):
            errors.append(f"records[{index}] Not Met requires finding_id")
    return errors
