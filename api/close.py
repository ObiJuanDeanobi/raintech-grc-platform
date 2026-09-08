"""Deterministic, declaration-driven, read-only close readiness checks."""
import json
from typing import Any
from fastapi import HTTPException

TARGET = "fieldwork_ready_for_generation"
_CHECKS = {"approved_profile_complete": "profile", "determinations_final": "determinations", "not_met_reconciled": "reconciliation", "sra_complete": "sra"}

def _block(items: list[dict[str, Any]], code: str, detail: str, check: str, link: str | None = None) -> None:
    item: dict[str, Any] = {"code": code, "detail": detail, "check": check}
    if link: item["link"] = link
    items.append(item)

def _approved_profile(connection: Any, project: Any) -> Any:
    active = project["active_profile_version_id"]
    if not active: return None
    return connection.execute("""SELECT versions.* FROM profile_versions versions
        JOIN profile_lifecycle_events events ON events.profile_version_id = versions.id
        WHERE versions.id = ? AND versions.project_id = ? AND events.status = 'Approved'
        ORDER BY events.rowid DESC LIMIT 1""", (active, project["id"])).fetchone()

def _scope_items(connection: Any, profile_id: str, declaration: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for target in declaration.get("scope_targets", []):
        scope_type = str(target["scope_type"])
        types = [str(value) for value in target.get("profile_item_types", [])]
        sections = [str(value) for value in target.get("profile_sections", [])]
        clauses: list[str] = []
        args: list[Any] = [profile_id]
        if types:
            placeholders = ",".join("?" for _ in types); clauses.append(f"items.item_type IN ({placeholders})"); args.extend(types)
        if sections:
            placeholders = ",".join("?" for _ in sections); clauses.append(f"values_row.section IN ({placeholders})"); args.extend(sections)
        if not clauses: continue
        rows = connection.execute(f"""SELECT DISTINCT items.client_key, COALESCE(items.client_key, values_row.field_key) AS name
            FROM profile_items items LEFT JOIN profile_field_values values_row ON values_row.profile_item_id = items.id AND values_row.profile_version_id = items.profile_version_id
            WHERE items.profile_version_id = ? AND ({' OR '.join(clauses)}) ORDER BY items.sort_order, items.client_key""", args).fetchall()
        items.extend({"scope_type": scope_type, "target_key": f"item:{row['client_key']}", "name": row["name"]} for row in rows)
    return items

def fieldwork_ready(connection: Any, project_id: str, assessment_id: str | None = None) -> dict[str, Any]:
    project = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None: raise HTTPException(status_code=404, detail="Project not found")
    framework = connection.execute("SELECT * FROM framework_versions WHERE id = ?", (project["framework_version_id"],)).fetchone()
    if framework is None: raise HTTPException(status_code=409, detail="Framework declaration not found")
    declarations = json.loads(framework["declarations_json"])
    close_decl = declarations.get("close_readiness", {}).get(TARGET)
    if not isinstance(close_decl, dict): raise HTTPException(status_code=409, detail="Close target is not declared by this framework")
    validator_names = close_decl.get("validators", [])
    blockers: list[dict[str, Any]] = []
    for name in validator_names:
        if name not in _CHECKS: _block(blockers, "unknown_validator", f"Unsupported close validator: {name}", "declaration")
    latest = connection.execute("SELECT * FROM profile_readiness_transitions WHERE project_id = ? ORDER BY rowid DESC LIMIT 1", (project_id,)).fetchone()
    approved = _approved_profile(connection, project)
    completion = declarations.get("profile_readiness", {}).get("profile_completion", {})
    if latest is None or latest["next_state"] != completion.get("state"): _block(blockers, "profile_not_complete", "Profile is not complete", "profile", f"/projects/{project_id}/profile")
    if approved is None: _block(blockers, "profile_not_approved", "An approved Profile is required", "profile", f"/projects/{project_id}/profile")
    if latest is not None:
        for field in json.loads(latest["unresolved_required_fields_json"] or "[]"): _block(blockers, "profile_unknown", f"Resolve required field: {field}", "profile", f"/projects/{project_id}/profile")
    if approved is not None:
        unknown = connection.execute("SELECT field_key FROM profile_field_values WHERE profile_version_id = ? AND lower(trim(value)) IN ('unknown', 'to determine', 'unknown / to determine')", (approved["id"],)).fetchall()
        for row in unknown: _block(blockers, "profile_unknown", f"Resolve Profile value: {row['field_key']}", "profile", f"/projects/{project_id}/profile")
    if assessment_id is None:
        active = connection.execute("SELECT assessment_id FROM project_active_assessments WHERE project_id = ?", (project_id,)).fetchone(); assessment_id = active["assessment_id"] if active else None
    assessment = None
    if assessment_id is not None:
        assessment = connection.execute("SELECT * FROM assessments WHERE id = ? AND project_id = ?", (assessment_id, project_id)).fetchone()
        if assessment is None: raise HTTPException(status_code=404, detail="Assessment not found for project")
        active = connection.execute("SELECT assessment_id FROM project_active_assessments WHERE project_id = ?", (project_id,)).fetchone()
        if active is None or active["assessment_id"] != assessment_id: _block(blockers, "assessment_not_active", "Close checks require the active assessment", "determinations", f"/projects/{project_id}/assessments/{assessment_id}")
    if assessment is None: _block(blockers, "assessment_missing", "Assessment is required", "determinations", f"/projects/{project_id}/assessments")
    else:
        records = connection.execute("SELECT record_id, carries_determination FROM framework_records WHERE framework_version_id = ? ORDER BY sort_order, record_id", (project["framework_version_id"],)).fetchall()
        for record_id in [row["record_id"] for row in records if row["carries_determination"]]:
            det = connection.execute("SELECT * FROM determinations WHERE assessment_id = ? AND record_id = ?", (assessment_id, record_id)).fetchone(); status = det["status"] if det else ""; link = f"/projects/{project_id}/assessments/{assessment_id}/records/{record_id}"
            if status in {"", "Blank", "Pending"}: _block(blockers, "determination_not_final", f"Final determination required: {record_id}", "determinations", link)
            elif status == "N/A" and not (det["na_rationale"] or "").strip(): _block(blockers, "na_rationale_missing", f"N/A rationale required: {record_id}", "determinations", link)
            elif status == "Not Met":
                rec = connection.execute("SELECT * FROM not_met_reconciliations WHERE project_id = ? AND assessment_id = ? AND record_id = ?", (project_id, assessment_id, record_id)).fetchone()
                if rec is None or not rec["finding_id"] or not rec["corrective_action_id"]: _block(blockers, "not_met_unreconciled", f"Reconcile Not Met: {record_id}", "reconciliation", f"{link}/reconciliation")
        sra = declarations.get("sra")
        if not isinstance(sra, dict): _block(blockers, "sra_not_declared", "SRA is not declared by the framework", "sra", f"/projects/{project_id}/sra")
        else:
            anchor = connection.execute("SELECT 1 FROM framework_records WHERE framework_version_id = ? AND record_id = ?", (project["framework_version_id"], sra.get("anchor_record_id", ""))).fetchone()
            if anchor is None: _block(blockers, "sra_anchor_missing", "Declared SRA anchor does not resolve", "sra", f"/projects/{project_id}/sra")
            if approved is not None:
                scope_items = _scope_items(connection, approved["id"], sra)
                if not scope_items: _block(blockers, "sra_incomplete", "Approved Profile contains no declared SRA scope facts", "sra", f"/projects/{project_id}/sra")
                for item in scope_items:
                    review = connection.execute("SELECT * FROM sra_scope_reviews WHERE project_id = ? AND profile_version_id = ? AND scope_type = ? AND target_key = ?", (project_id, approved["id"], item["scope_type"], item["target_key"])).fetchone()
                    if review is None: _block(blockers, "sra_incomplete", f"Review {item['scope_type']} scope: {item['name']}", "sra", f"/projects/{project_id}/sra/scope")
                    elif not review["included"] and not (review["exclusion_rationale"] or "").strip(): _block(blockers, "sra_exclusion_rationale_missing", f"Explain excluded {item['scope_type']} scope: {item['name']}", "sra", f"/projects/{project_id}/sra/scope")
                risks = connection.execute("SELECT * FROM risks WHERE project_id = ? AND assessment_id = ? AND profile_version_id = ?", (project_id, assessment_id, approved["id"])).fetchall(); required_fields = [str(value) for value in sra.get("risk_required_fields", [])]
                if not risks: _block(blockers, "risk_incomplete", "Record at least one complete SRA risk", "sra", f"/projects/{project_id}/risks")
                for risk in risks:
                    missing = [field for field in required_fields if not str(risk[field] or "").strip()]
                    if missing: _block(blockers, "risk_incomplete", f"Complete risk {risk['title']}: {', '.join(missing)}", "sra", f"/projects/{project_id}/risks/{risk['id']}")
            elif approved is None:
                _block(blockers, "sra_not_approved", "Approve a Profile before completing SRA scope", "sra", f"/projects/{project_id}/sra")
                _block(blockers, "risk_review_missing", "Complete and review at least one SRA risk", "sra", f"/projects/{project_id}/risks")
    if assessment is None and isinstance(declarations.get("sra"), dict):
        _block(blockers, "sra_not_approved", "Approve a Profile and complete SRA scope before close", "sra", f"/projects/{project_id}/sra")
        _block(blockers, "risk_review_missing", "Complete and review at least one SRA risk", "sra", f"/projects/{project_id}/risks")
    return _result(blockers, validator_names, project_id, assessment_id, close_decl, framework["id"])

def _result(blockers: list[dict[str, Any]], validator_names: list[str], project_id: str, assessment_id: str | None, close_decl: dict[str, Any], framework_id: str) -> dict[str, Any]:
    checks = []
    for name in validator_names:
        check = _CHECKS.get(name, "declaration"); blocked = check == "declaration" or any(item.get("check") == check for item in blockers); checks.append({"name": name, "status": "Blocked" if blocked else "Ready", "check": check})
    links = sorted({item["link"] for item in blockers if item.get("link")})
    return {"target": TARGET, "status": "Ready" if not blockers else "Blocked", "ready": not blockers, "checks": checks, "blockers": blockers, "links": [{"href": link, "label": "Resolve blocker"} for link in links], "framework_version_id": framework_id, "project_id": project_id, "assessment_id": assessment_id, "informational": {name: "not_applicable" for name in close_decl.get("informational", [])}}
