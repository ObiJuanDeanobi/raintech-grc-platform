"""Deterministic HIPAA report and POA&M rendering.

The renderer deliberately consumes a plain, immutable source snapshot.  It does
not query the live database, infer framework controls, or mutate assessment
records.  Callers should build the snapshot at the issuance boundary and retain
its canonical hash with the generated artifacts.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping

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

POAM_COLUMNS = (
    "POA&M ID", "Control Reference", "Requirement", "Control Group",
    "Control Description", "Finding ID", "Action ID", "Action Owner",
    "Risk Rating", "Status", "Scheduled Completion", "Milestone",
    "Resources", "Validation Owner", "Validation Evidence", "Closure Date",
    "Source Snapshot ID",
)

_TOKEN = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


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
    if isinstance(value, (list, tuple, set)):
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
        "client_name": _none(profile.get("client_name")), "project_name": _none(assessment.get("project_name")),
        "assessment_start_date": _none(assessment.get("start_date")), "assessment_end_date": _none(assessment.get("end_date")),
        "assessment_revision": _none(assessment.get("revision")), "profile_snapshot_id": _none(profile.get("snapshot_id")),
        "source_snapshot_id": _none(s.get("snapshot_id")), "template_version": _none(s.get("template_version", "hipaa-v2")),
        "framework_title": _none(framework.get("title")), "framework_version": _none(framework.get("version", framework.get("id"))),
        "framework_declaration_id": _none(framework.get("declaration_id", framework.get("id"))),
        "assessment_source_sha256": s["source_sha256"], "empty_state_none_recorded": "None recorded",
        "met_count": str(statuses.count("Met")), "not_met_count": str(statuses.count("Not Met")),
        "not_applicable_count": str(statuses.count("N/A")),
        "assessment_decision": _none(assessment.get("decision")), "issuance_decision": _none(assessment.get("issuance_decision")),
    }
    # Every remaining approved token is intentionally resolved to a safe empty state.
    return values


def render_report(template_path: Path, output_path: Path, snapshot: Mapping[str, Any]) -> str:
    """Render named fields into a DOCX while preserving the approved package."""
    values = report_values(snapshot)
    source = BytesIO()
    with zipfile.ZipFile(template_path, "r") as zin, zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text = data.decode("utf-8")
                data = _TOKEN.sub(lambda match: values.get(match.group(1), "None recorded").replace("&", "&amp;"), text).encode("utf-8")
            zout.writestr(item, data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(source.getvalue())
    return snapshot_sha256(snapshot)


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

