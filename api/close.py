"""Deterministic, read-only close readiness evaluation."""
import json
from typing import Any

from fastapi import HTTPException


def fieldwork_ready(connection: Any, project_id: str, assessment_id: str | None = None) -> dict[str, Any]:
    project = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        raise HTTPException(404, "Project not found")
    framework = connection.execute("SELECT * FROM framework_versions WHERE id = ?", (project["framework_version_id"],)).fetchone()
    if framework is None:
        raise HTTPException(409, "Framework declaration not found")
    declarations = json.loads(framework["declarations_json"])
    blockers: list[dict[str, str]] = []
    latest = connection.execute("SELECT * FROM profile_readiness_transitions WHERE project_id = ? ORDER BY rowid DESC LIMIT 1", (project_id,)).fetchone()
    approved = connection.execute("SELECT * FROM profile_versions WHERE project_id = ? AND status = 'Approved' ORDER BY version_number DESC LIMIT 1", (project_id,)).fetchone()
    if latest is None or latest["next_state"] != declarations["profile_readiness"]["profile_completion"]["state"]:
        blockers.append({"code": "profile_not_complete", "detail": "Profile is not complete"})
    if approved is None:
        blockers.append({"code": "profile_not_approved", "detail": "An approved Profile is required"})
    if latest:
        unresolved = json.loads(latest["unresolved_required_fields_json"] or "[]")
        for field in unresolved:
            blockers.append({"code": "profile_unknown", "detail": f"Resolve required field: {field}"})
    assessment = connection.execute("SELECT * FROM assessments WHERE project_id = ? AND (? IS NULL OR id = ?)", (project_id, assessment_id, assessment_id)).fetchone()
    if assessment_id and assessment is None:
        raise HTTPException(404, "Assessment not found for project")
    if approved is not None:
        unknown = connection.execute("SELECT field_key FROM profile_field_values WHERE profile_version_id = ? AND lower(trim(value)) IN ('unknown', 'to determine', 'unknown / to determine')", (approved["id"],)).fetchall()
        for row in unknown:
            blockers.append({"code": "profile_unknown", "detail": f"Resolve Profile value: {row['field_key']}"})
    if assessment is None:
        blockers.append({"code": "assessment_missing", "detail": "Assessment is required"})
        return {"target": "fieldwork_ready_for_generation", "status": "Blocked", "ready": False, "checks": [], "blockers": blockers, "links": [], "informational": {"package": "not_applicable", "review": "not_applicable", "sign": "not_applicable", "backup": "not_applicable", "snapshot": "not_applicable"}}
    records = connection.execute("SELECT record_id, carries_determination FROM framework_records WHERE framework_version_id = ?", (project["framework_version_id"],)).fetchall()
    parents = {row["record_id"] for row in records if not row["carries_determination"]}
    required = [row["record_id"] for row in records if row["carries_determination"] and row["record_id"] not in parents]
    for record_id in required:
        det = connection.execute("SELECT * FROM determinations WHERE assessment_id = ? AND record_id = ?", (assessment["id"], record_id)).fetchone()
        if det is None or det["status"] in {"", "Pending"}:
            blockers.append({"code": "determination_not_final", "detail": f"Final determination required: {record_id}"})
        elif det["status"] == "N/A" and not det["na_rationale"].strip():
            blockers.append({"code": "na_rationale_missing", "detail": f"N/A rationale required: {record_id}"})
        elif det["status"] == "Not Met":
            rec = connection.execute("SELECT * FROM not_met_reconciliations WHERE assessment_id = ? AND record_id = ?", (assessment["id"], record_id)).fetchone()
            if rec is None or not rec["finding_id"] or not rec["corrective_action_id"]:
                blockers.append({"code": "not_met_unreconciled", "detail": f"Reconcile Not Met: {record_id}"})
    sra = declarations.get("sra", {})
    anchor = connection.execute("SELECT 1 FROM framework_records WHERE framework_version_id = ? AND record_id = ?", (project["framework_version_id"], sra.get("anchor_record_id", ""))).fetchone()
    if anchor is None:
        blockers.append({"code": "sra_anchor_missing", "detail": "Declared SRA anchor does not resolve"})
    checks = [{"name": name, "status": "Blocked" if any(b["code"].startswith(name.split("_")[0]) for b in blockers) else "Ready"} for name in declarations.get("close_readiness", {}).get("fieldwork_ready_for_generation", {}).get("validators", [])]
    return {"target": "fieldwork_ready_for_generation", "status": "Ready" if not blockers else "Blocked", "ready": not blockers, "checks": checks, "blockers": blockers, "links": [], "informational": {"package": "not_applicable", "review": "not_applicable", "sign": "not_applicable", "backup": "not_applicable", "snapshot": "not_applicable"}}
