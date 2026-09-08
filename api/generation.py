"""Deterministic, project-scoped HIPAA package generation."""
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import sqlite3

from api.close import fieldwork_ready
from api.storage import FileStorage

TEMPLATE_ROOT = "docs/templates/hipaa/v2"
TEMPLATES = (("assessment_report", "RainTech_HIPAA_Combined_Assessment_Report_v2.docx"), ("poam", "RainTech_HIPAA_POAM_v2.xlsx"))

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _json_rows(connection: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, args)]

def generate_package(connection: sqlite3.Connection, storage: FileStorage, root: Path,
                     project_id: str, assessment_id: str, *, actor_id: str = "johnathan") -> dict:
    """Generate both approved HIPAA artifacts atomically after the readiness gate."""
    assessment = connection.execute("SELECT * FROM assessments WHERE id = ? AND project_id = ?", (assessment_id, project_id)).fetchone()
    if assessment is None:
        raise ValueError("Assessment does not belong to project")
    decision = fieldwork_ready(connection, project_id, assessment_id)
    if decision.get("decision") != "ready":
        raise ValueError("Assessment is not ready for generation")
    profile = connection.execute("SELECT id, revision_token, status FROM profile_versions WHERE project_id = ? AND status IN ('Approved','Reviewed') ORDER BY created_at DESC LIMIT 1", (project_id,)).fetchone()
    source = {"project_id": project_id, "assessment_id": assessment_id, "assessment_revision": assessment["revision_number"],
              "profile": dict(profile) if profile else None,
              "determinations": _json_rows(connection, "SELECT * FROM determinations WHERE assessment_id = ?", (assessment_id,)),
              "reconciliations": _json_rows(connection, "SELECT * FROM not_met_reconciliations WHERE assessment_id = ?", (assessment_id,)),
              "sra_scope": _json_rows(connection, "SELECT * FROM sra_scope_reviews WHERE project_id = ?", (project_id,)),
              "readiness": decision}
    source_json = json.dumps(source, sort_keys=True, separators=(",", ":"))
    source_hash = sha256(source_json.encode()).hexdigest()
    snapshot_id, attempt_id, package_id = str(uuid4()), str(uuid4()), str(uuid4())
    created = _now()
    connection.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?,?,?,?,?)", (snapshot_id, project_id, assessment_id, assessment["revision_number"], profile["id"] if profile else None, profile["revision_token"] if profile else "", source_json, source_hash, created))
    connection.execute("INSERT INTO generation_attempts VALUES (?,?,?,?,?,?,?,?,?)", (attempt_id, project_id, assessment_id, "fieldwork_ready_for_generation", "staged", snapshot_id, None, created, None))
    staged: list[tuple[str, str, str, bytes]] = []
    try:
        components = []
        for kind, filename in TEMPLATES:
            content = (root / TEMPLATE_ROOT / filename).read_bytes()
            component_id = str(uuid4())
            staged_path, final_path = storage.stage(project_id, component_id, filename, content)
            staged.append((staged_path, final_path, component_id, content))
            components.append({"id": component_id, "kind": kind, "filename": filename, "path": final_path, "sha256": sha256(content).hexdigest(), "bytes": len(content)})
        manifest = {"project_id": project_id, "assessment_id": assessment_id, "source_snapshot_sha256": source_hash, "template_version": "hipaa-v2", "components": components}
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        package_hash = sha256(manifest_json.encode()).hexdigest()
        connection.execute("INSERT INTO generated_packages VALUES (?,?,?,?,?,?,?,?,?,?)", (package_id, project_id, assessment_id, attempt_id, snapshot_id, "hipaa-v2", "staged", manifest_json, package_hash, created))
        for item in components:
            connection.execute("INSERT INTO generated_components VALUES (?,?,?,?,?,?,?,?,?)", (item["id"], project_id, package_id, item["kind"], item["filename"], item["path"], item["sha256"], item["bytes"], created))
        for staged_path, final_path, *_ in staged:
            storage.promote(staged_path, final_path)
        connection.execute("UPDATE generated_packages SET state='promoted' WHERE id=?", (package_id,))
        connection.execute("UPDATE generation_attempts SET state='promoted', completed_at=? WHERE id=?", (_now(), attempt_id))
        return {"id": package_id, "project_id": project_id, "assessment_id": assessment_id, "state": "promoted", "manifest": manifest}
    except Exception as exc:
        for staged_path, final_path, *_ in staged:
            storage.delete(staged_path)
        connection.execute("UPDATE generation_attempts SET state='failed', error=?, completed_at=? WHERE id=?", (str(exc), _now(), attempt_id))
        raise

def list_packages(connection: sqlite3.Connection, project_id: str) -> list[dict]:
    return [dict(row) for row in connection.execute("SELECT * FROM generated_packages WHERE project_id=? ORDER BY created_at DESC", (project_id,))]
