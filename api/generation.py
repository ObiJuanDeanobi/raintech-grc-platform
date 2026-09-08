"""Deterministic, project-scoped HIPAA package generation."""
import json, sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from api.close import fieldwork_ready
from api.renderers.hipaa import render_report, validate_snapshot
from api.storage import FileStorage

TEMPLATE_ROOT="docs/templates/hipaa/v2"
TEMPLATES=(("assessment_report","RainTech_HIPAA_Combined_Assessment_Report_v2.docx"),("poam","RainTech_HIPAA_POAM_v2.xlsx"))
def _now(): return datetime.now(UTC).isoformat()
def _rows(c, table, where, args=()):
    try: return [dict(r) for r in c.execute(f"SELECT * FROM {table} WHERE {where}",args)]
    except sqlite3.OperationalError: return []
def _snapshot(c, project_id, assessment_id, assessment):
    profile=c.execute("SELECT pv.* FROM profile_versions pv JOIN profile_lifecycle_events le ON le.profile_version_id=pv.id WHERE pv.project_id=? AND le.status='Approved' ORDER BY le.created_at DESC LIMIT 1",(project_id,)).fetchone()
    if profile is None: raise ValueError("An approved Profile lifecycle snapshot is required")
    framework=c.execute("SELECT * FROM framework_versions WHERE id=?",(assessment["framework_version_id"],)).fetchone()
    source={"snapshot_id":str(uuid4()),"template_version":"hipaa-v2","framework":{"id":assessment["framework_version_id"],"version":dict(framework) if framework else {},"declarations":_rows(c,"framework_declarations","framework_version_id=?",(assessment["framework_version_id"],))},"assessment":dict(assessment),"profile":{**dict(profile),"snapshot_id":profile["id"]},"records":_rows(c,"framework_records","framework_version_id=?",(assessment["framework_version_id"],)),"risks":_rows(c,"risks","project_id=?",(project_id,)),"profile_values":_rows(c,"profile_field_values","profile_version_id=?",(profile["id"],)),"determinations":_rows(c,"determinations","assessment_id=?",(assessment_id,)),"findings":_rows(c,"findings","project_id=?",(project_id,)),"corrective_actions":_rows(c,"corrective_actions","project_id=?",(project_id,)),"reconciliations":_rows(c,"not_met_reconciliations","project_id=?",(project_id,)),"sra_scope":_rows(c,"sra_scope_reviews","project_id=?",(project_id,)),"evidence_versions":_rows(c,"evidence_versions","project_id=?",(project_id,)),"readiness":fieldwork_ready(c,project_id,assessment_id)}
    errors=validate_snapshot(source)
    if errors: raise ValueError("Snapshot is not renderable: "+"; ".join(errors))
    encoded=json.dumps(source,sort_keys=True,separators=(",",":")); return source,sha256(encoded.encode()).hexdigest(),profile
def generate_package(connection: sqlite3.Connection, storage: FileStorage, root: Path, project_id: str, assessment_id: str, *, actor_id="johnathan"):
    assessment=connection.execute("SELECT * FROM assessments WHERE id=? AND project_id=?",(assessment_id,project_id)).fetchone()
    if assessment is None: raise ValueError("Assessment does not belong to project")
    if fieldwork_ready(connection,project_id,assessment_id).get("decision") != "ready": raise ValueError("Assessment is not ready for generation")
    source,source_hash,profile=_snapshot(connection,project_id,assessment_id,assessment); snapshot_id,attempt_id,package_id,created=source["snapshot_id"],str(uuid4()),str(uuid4()),_now(); source_json=json.dumps(source,sort_keys=True,separators=(",",":"))
    connection.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?,?,?,?,?)",(snapshot_id,project_id,assessment_id,assessment["revision_number"],profile["id"],profile["revision_token"],source_json,source_hash,created)); connection.execute("INSERT INTO generation_attempts VALUES (?,?,?,?,?,?,?,?,?)",(attempt_id,project_id,assessment_id,"fieldwork_ready_for_generation","staged",snapshot_id,None,created,None))
    staged=[]; promoted=[]
    try:
        components=[]
        for kind,filename in TEMPLATES:
            template=root/TEMPLATE_ROOT/filename; component_id=str(uuid4()); content=template.read_bytes()
            if kind=="assessment_report":
                out=root/"data"/"generation-staging"/f"{component_id}-{filename}"; render_report(template,out,source); content=out.read_bytes(); out.unlink(missing_ok=True)
            staged_path,final_path=storage.stage(project_id,component_id,filename,content); staged.append((staged_path,final_path)); components.append({"id":component_id,"kind":kind,"filename":filename,"path":final_path,"sha256":sha256(content).hexdigest(),"bytes":len(content)})
        manifest={"project_id":project_id,"assessment_id":assessment_id,"source_snapshot_sha256":source_hash,"template_version":"hipaa-v2","components":components}; manifest_json=json.dumps(manifest,sort_keys=True,separators=(",",":")); connection.execute("INSERT INTO generated_packages VALUES (?,?,?,?,?,?,?,?,?,?)",(package_id,project_id,assessment_id,attempt_id,snapshot_id,"hipaa-v2","staged",manifest_json,sha256(manifest_json.encode()).hexdigest(),created))
        for item in components: connection.execute("INSERT INTO generated_components VALUES (?,?,?,?,?,?,?,?,?)",(item["id"],project_id,package_id,item["kind"],item["filename"],item["path"],item["sha256"],item["bytes"],created))
        for staged_path,final_path in staged: storage.promote(staged_path,final_path); promoted.append(final_path)
        connection.execute("UPDATE generated_packages SET state='promoted' WHERE id=?",(package_id,)); connection.execute("UPDATE generation_attempts SET state='promoted',completed_at=? WHERE id=?",(_now(),attempt_id)); return {"id":package_id,"project_id":project_id,"assessment_id":assessment_id,"state":"promoted","manifest":manifest}
    except Exception as exc:
        for path in [p for p,_ in staged]+promoted: storage.delete(path)
        connection.execute("UPDATE generation_attempts SET state='failed',error=?,completed_at=? WHERE id=?",(str(exc),_now(),attempt_id)); raise
def list_packages(connection,project_id): return [dict(r) for r in connection.execute("SELECT * FROM generated_packages WHERE project_id=? ORDER BY created_at DESC",(project_id,))]
