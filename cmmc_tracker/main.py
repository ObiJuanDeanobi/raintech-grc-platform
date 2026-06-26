from __future__ import annotations

from typing import Annotated

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import STATUSES, connect, init_db
from .platform_services import (
    create_assessment,
    create_client,
    create_quote_record,
    evidence_report_xlsx,
    export_platform_package,
    generate_documents,
    get_assessment,
    get_client,
    get_profile,
    get_result,
    latest_quote,
    link_evidence,
    list_assessments,
    list_clients,
    list_controls,
    list_documents,
    list_evidence_library,
    poam_report_xlsx,
    poam_rows,
    seed_default_client,
    tailored_evidence_guidance,
    unlink_evidence,
    update_client,
    update_profile,
    update_result,
    save_document,
)
from .paths import PROJECT_ROOT, data_dir
from .services import (
    attach_evidence,
    completion_csv,
    completion_xlsx,
    delete_evidence,
    detach_evidence,
    export_zip,
    replace_evidence,
    store_upload,
)


app = FastAPI(title="CMMC L2 Evidence Tracker")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_default_client()


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


@app.get("/platform")
def platform_home(request: Request):
    return templates.TemplateResponse("platform.html", {"request": request})


@app.get("/")
def dashboard(request: Request):
    with connect() as conn:
        overall = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN os.status = 'Captured' THEN 1 ELSE 0 END) AS captured,
                SUM(CASE WHEN os.status = 'Not Captured' THEN 1 ELSE 0 END) AS not_captured,
                SUM(CASE WHEN os.status = 'Escalating' THEN 1 ELSE 0 END) AS escalating,
                SUM(CASE WHEN evidence_count.count > 0 THEN 1 ELSE 0 END) AS with_evidence
            FROM objectives o
            JOIN objective_status os ON os.objective_id = o.id
            LEFT JOIN (
                SELECT objective_id, COUNT(*) AS count
                FROM objective_evidence
                GROUP BY objective_id
            ) evidence_count ON evidence_count.objective_id = o.id
            """
        ).fetchone()
        domains = conn.execute(
            """
            SELECT
                d.code,
                d.name,
                COUNT(o.id) AS total,
                SUM(CASE WHEN os.status = 'Captured' THEN 1 ELSE 0 END) AS captured,
                SUM(CASE WHEN os.status = 'Not Captured' THEN 1 ELSE 0 END) AS not_captured,
                SUM(CASE WHEN os.status = 'Escalating' THEN 1 ELSE 0 END) AS escalating,
                SUM(CASE WHEN evidence_count.count > 0 THEN 1 ELSE 0 END) AS with_evidence
            FROM domains d
            JOIN requirements r ON r.domain_code = d.code
            JOIN objectives o ON o.requirement_id = r.id
            JOIN objective_status os ON os.objective_id = o.id
            LEFT JOIN (
                SELECT objective_id, COUNT(*) AS count
                FROM objective_evidence
                GROUP BY objective_id
            ) evidence_count ON evidence_count.objective_id = o.id
            GROUP BY d.code
            ORDER BY d.sort_order
            """
        ).fetchall()
    percent = round((overall["captured"] or 0) / overall["total"] * 100, 1) if overall["total"] else 0
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "overall": overall,
            "domains": domains,
            "percent": percent,
        },
    )


@app.post("/settings")
def update_settings(
    company_id: Annotated[str, Form()],
    company_name: Annotated[str, Form()],
):
    with connect() as conn:
        conn.execute(
            "UPDATE settings SET company_id = ?, company_name = ? WHERE id = 1",
            (company_id.strip() or "ID", company_name.strip() or "COMPANY"),
        )
    return redirect("/")


@app.get("/objectives")
def objectives(
    request: Request,
    domain: str = "",
    status: str = "",
    missing: str = "",
    q: str = "",
):
    filters = []
    params: list[str] = []
    if domain:
        filters.append("d.code = ?")
        params.append(domain)
    if status:
        filters.append("os.status = ?")
        params.append(status)
    if q:
        filters.append("(o.id LIKE ? OR r.id LIKE ? OR r.name LIKE ? OR r.text LIKE ? OR o.text LIKE ?)")
        term = f"%{q}%"
        params.extend([term, term, term, term, term])
    where = "WHERE " + " AND ".join(filters) if filters else ""
    having = "HAVING evidence_count = 0" if missing == "1" else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                d.code AS domain_code,
                d.name AS domain,
                r.id AS requirement_id,
                r.name AS requirement_name,
                o.id AS objective_id,
                o.text AS objective_text,
                os.status,
                COUNT(oe.evidence_id) AS evidence_count
            FROM objectives o
            JOIN requirements r ON r.id = o.requirement_id
            JOIN domains d ON d.code = r.domain_code
            JOIN objective_status os ON os.objective_id = o.id
            LEFT JOIN objective_evidence oe ON oe.objective_id = o.id
            {where}
            GROUP BY o.id
            {having}
            ORDER BY d.sort_order, r.id, o.letter
            """,
            params,
        ).fetchall()
        domains = conn.execute("SELECT code, name FROM domains ORDER BY sort_order").fetchall()
    return templates.TemplateResponse(
        "objectives.html",
        {
            "request": request,
            "rows": rows,
            "domains": domains,
            "statuses": STATUSES,
            "filters": {"domain": domain, "status": status, "missing": missing, "q": q},
        },
    )


@app.get("/objectives/{objective_id}")
def objective_detail(request: Request, objective_id: str):
    with connect() as conn:
        objective = conn.execute(
            """
            SELECT
                d.name AS domain,
                d.code AS domain_code,
                r.id AS requirement_id,
                r.name AS requirement_name,
                r.text AS requirement_text,
                r.potential_methods,
                r.discussion,
                r.further_discussion,
                o.id AS objective_id,
                o.text AS objective_text,
                os.status,
                os.notes
            FROM objectives o
            JOIN requirements r ON r.id = o.requirement_id
            JOIN domains d ON d.code = r.domain_code
            JOIN objective_status os ON os.objective_id = o.id
            WHERE o.id = ?
            """,
            (objective_id,),
        ).fetchone()
        attached = conn.execute(
            """
            SELECT e.*
            FROM objective_evidence oe
            JOIN evidence e ON e.id = oe.evidence_id
            WHERE oe.objective_id = ?
            ORDER BY e.title
            """,
            (objective_id,),
        ).fetchall()
        available = conn.execute(
            """
            SELECT e.*, COUNT(oe.objective_id) AS mapped_count
            FROM evidence e
            LEFT JOIN objective_evidence oe ON oe.evidence_id = e.id
            WHERE e.id NOT IN (
                SELECT evidence_id FROM objective_evidence WHERE objective_id = ?
            )
            GROUP BY e.id
            ORDER BY e.title
            """,
            (objective_id,),
        ).fetchall()
        ordered_objectives = conn.execute(
            """
            SELECT o.id
            FROM objectives o
            JOIN requirements r ON r.id = o.requirement_id
            JOIN domains d ON d.code = r.domain_code
            ORDER BY d.sort_order, r.id, o.letter
            """
        ).fetchall()
    if not objective:
        return Response("Objective not found", status_code=404)
    ordered_ids = [row["id"] for row in ordered_objectives]
    current_index = ordered_ids.index(objective_id)
    previous_objective = ordered_ids[current_index - 1] if current_index > 0 else None
    next_objective = ordered_ids[current_index + 1] if current_index < len(ordered_ids) - 1 else None
    return templates.TemplateResponse(
        "objective_detail.html",
        {
            "request": request,
            "objective": objective,
            "previous_objective": previous_objective,
            "next_objective": next_objective,
            "attached": attached,
            "available": available,
            "statuses": STATUSES,
        },
    )


@app.post("/objectives/{objective_id}/status")
def update_objective_status(
    objective_id: str,
    status: Annotated[str, Form()],
    notes: Annotated[str, Form()] = "",
):
    if status not in STATUSES:
        status = "Not Captured"
    with connect() as conn:
        conn.execute(
            """
            UPDATE objective_status
            SET status = ?, notes = ?, updated_at = datetime('now')
            WHERE objective_id = ?
            """,
            (status, notes.strip(), objective_id),
        )
    return redirect(f"/objectives/{objective_id}")


@app.post("/objectives/{objective_id}/attach")
def attach_existing_evidence(
    objective_id: str,
    evidence_id: Annotated[int, Form()],
):
    attach_evidence(objective_id, evidence_id)
    return redirect(f"/objectives/{objective_id}")


@app.post("/objectives/{objective_id}/detach")
def detach_existing_evidence(
    objective_id: str,
    evidence_id: Annotated[int, Form()],
):
    detach_evidence(objective_id, evidence_id)
    return redirect(f"/objectives/{objective_id}")


@app.post("/objectives/{objective_id}/upload")
def upload_for_objective(
    objective_id: str,
    evidence_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    source: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    evidence_id = store_upload(
        evidence_file.file,
        evidence_file.filename or "evidence",
        title,
        source,
        notes,
    )
    attach_evidence(objective_id, evidence_id)
    return redirect(f"/objectives/{objective_id}")


@app.get("/evidence")
def evidence_library(request: Request):
    with connect() as conn:
        evidence = conn.execute(
            """
            SELECT e.*, COUNT(oe.objective_id) AS mapped_count
            FROM evidence e
            LEFT JOIN objective_evidence oe ON oe.evidence_id = e.id
            GROUP BY e.id
            ORDER BY e.uploaded_at DESC
            """
        ).fetchall()
        objectives = conn.execute(
            """
            SELECT o.id, r.name AS requirement_name
            FROM objectives o
            JOIN requirements r ON r.id = o.requirement_id
            ORDER BY o.id
            """
        ).fetchall()
    return templates.TemplateResponse(
        "evidence.html",
        {"request": request, "evidence": evidence, "objectives": objectives},
    )


@app.post("/evidence/upload")
def upload_evidence(
    evidence_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    source: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
    objective_ids: Annotated[list[str], Form()] = [],
):
    evidence_id = store_upload(
        evidence_file.file,
        evidence_file.filename or "evidence",
        title,
        source,
        notes,
    )
    for objective_id in objective_ids:
        attach_evidence(objective_id, evidence_id)
    return redirect("/evidence")


@app.post("/evidence/{evidence_id}/replace")
def replace_evidence_file(
    evidence_id: int,
    evidence_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    source: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    replace_evidence(
        evidence_id,
        evidence_file.file,
        evidence_file.filename or "evidence",
        title,
        source,
        notes,
    )
    return redirect("/evidence")


@app.post("/evidence/{evidence_id}/delete")
def delete_evidence_file(evidence_id: int):
    delete_evidence(evidence_id)
    return redirect("/evidence")


@app.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int):
    with connect() as conn:
        evidence = conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
    if not evidence:
        return Response("Evidence not found", status_code=404)
    return FileResponse(
        data_dir() / evidence["stored_path"],
        filename=evidence["original_filename"],
        media_type="application/octet-stream",
    )


@app.get("/exports/zip")
def download_zip():
    path = export_zip()
    return FileResponse(path, filename=path.name, media_type="application/zip")


@app.get("/reports/completion")
def completion_report(format: str = "xlsx"):
    if format == "csv":
        return Response(
            completion_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cmmc_l2_completion.csv"},
        )
    return Response(
        completion_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cmmc_l2_completion.xlsx"},
    )


# ---------------------------------------------------------------------------
# CMMC-first GRC platform API
# ---------------------------------------------------------------------------


@app.get("/api/clients")
def api_clients():
    return list_clients()


@app.post("/api/clients")
def api_create_client(payload: Annotated[dict, Body()]):
    return create_client(payload)


@app.get("/api/clients/{client_id}")
def api_get_client(client_id: str):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.put("/api/clients/{client_id}")
def api_update_client(client_id: str, payload: Annotated[dict, Body()]):
    client = update_client(client_id, payload)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.get("/api/clients/{client_id}/profile")
def api_get_profile(client_id: str):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return get_profile(client_id)


@app.put("/api/clients/{client_id}/profile")
def api_update_profile(client_id: str, payload: Annotated[dict, Body()]):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return update_profile(client_id, payload, create_quote=bool(payload.get("create_quote")))


@app.post("/api/clients/{client_id}/quote")
def api_create_quote(client_id: str):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return create_quote_record(client_id)


@app.get("/api/clients/{client_id}/quote")
def api_latest_quote(client_id: str):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return latest_quote(client_id) or {}


@app.post("/api/leads/convert")
def api_convert_lead(payload: Annotated[dict, Body()]):
    client_payload = {
        "name": payload.get("company") or payload.get("name") or "New Lead",
        "primary_contact_name": payload.get("name") or "",
        "primary_contact_email": payload.get("email") or "",
        "primary_contact_phone": payload.get("phone") or "",
        "notes": payload.get("notes") or "Converted from readiness/quote intake.",
    }
    client = create_client(client_payload)
    profile_payload = {
        "legal_name": client["name"],
        "system_name": f"{client['name']} CUI Environment",
        "environment_shape": payload.get("environment_shape") or payload.get("environmentShape") or "",
        "required_cloud": payload.get("required_cloud") or payload.get("requiredCloud") or "",
        "current_cloud": payload.get("cloud") or payload.get("current_cloud") or "",
        "cui_type": payload.get("cui_type") or payload.get("cuiType") or "",
        "cui_flow": payload.get("cui_flow") or "",
        "cui_location": payload.get("cui_location") or payload.get("cuiLocation") or "",
        "cui_users": payload.get("cui_users") or payload.get("cuiUsers") or None,
        "timeline": payload.get("timeline") or "",
        "external_access": payload.get("external_access") or payload.get("externalAccess") or "",
        "internal_owner": payload.get("internal_owner") or payload.get("internalOwner") or "",
        "ongoing_support": payload.get("ongoing") or payload.get("ongoing_support") or "",
        "quote_answers": payload,
        "questionnaire_complete": False,
    }
    profile = update_profile(client["id"], profile_payload, create_quote=True)
    assessment = create_assessment(client["id"], "CMMC Level 2 Readiness")
    return {"client": get_client(client["id"]), "profile": profile, "assessment": assessment}


@app.get("/api/assessments")
def api_assessments(client_id: str = ""):
    return list_assessments(client_id or None)


@app.post("/api/assessments")
def api_create_assessment(payload: Annotated[dict, Body()]):
    client_id = payload.get("client_id")
    if not client_id or not get_client(client_id):
        raise HTTPException(status_code=400, detail="Valid client_id is required")
    return create_assessment(
        client_id,
        payload.get("name") or "CMMC Level 2 Readiness",
        payload.get("description") or "",
    )


@app.get("/api/assessments/{assessment_id}")
def api_assessment(assessment_id: str):
    assessment = get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@app.get("/api/assessments/{assessment_id}/score")
def api_assessment_score(assessment_id: str):
    assessment = get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment["score"]


@app.get("/api/assessments/{assessment_id}/results")
def api_assessment_results(
    assessment_id: str,
    family: str = "",
    status: str = "",
    missing: bool = False,
    q: str = "",
):
    if not get_assessment(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    return list_controls(assessment_id, family, status, missing, q)


@app.get("/api/controls/families")
def api_control_families():
    with connect() as conn:
        rows = conn.execute("SELECT code, name FROM domains ORDER BY sort_order").fetchall()
    return [dict(row) for row in rows]


@app.get("/api/results/{result_id}")
def api_get_result(result_id: str):
    result = get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@app.patch("/api/results/{result_id}")
def api_update_result(result_id: str, payload: Annotated[dict, Body()]):
    result = update_result(result_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@app.post("/api/results/{result_id}/evidence")
def api_upload_result_evidence(
    result_id: str,
    evidence_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    source: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    if not get_result(result_id):
        raise HTTPException(status_code=404, detail="Result not found")
    evidence_id = store_upload(
        evidence_file.file,
        evidence_file.filename or "evidence",
        title,
        source,
        notes,
    )
    link_evidence(result_id, evidence_id)
    return get_result(result_id)


@app.post("/api/results/{result_id}/link")
def api_link_evidence(result_id: str, payload: Annotated[dict, Body()]):
    if not get_result(result_id):
        raise HTTPException(status_code=404, detail="Result not found")
    evidence_id = int(payload.get("evidence_id"))
    link_evidence(result_id, evidence_id)
    return get_result(result_id)


@app.delete("/api/results/{result_id}/evidence/{evidence_id}")
def api_unlink_evidence(result_id: str, evidence_id: int):
    unlink_evidence(result_id, evidence_id)
    return {"ok": True}


@app.get("/api/evidence")
def api_evidence_library(assessment_id: str = ""):
    return list_evidence_library(assessment_id or None)


@app.get("/api/tailored-evidence/{client_id}/{objective_id}")
def api_tailored_evidence(client_id: str, objective_id: str):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    guidance = tailored_evidence_guidance(client_id, objective_id)
    if not guidance:
        raise HTTPException(status_code=404, detail="Objective not found")
    return guidance


@app.get("/api/assessments/{assessment_id}/poam")
def api_poam(assessment_id: str):
    if not get_assessment(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    return poam_rows(assessment_id)


@app.post("/api/clients/{client_id}/documents/generate")
def api_generate_documents(client_id: str, assessment_id: str = ""):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return {"generated": generate_documents(client_id, assessment_id or None)}


@app.get("/api/clients/{client_id}/documents")
def api_documents(client_id: str, assessment_id: str = ""):
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    return list_documents(client_id, assessment_id or None)


@app.patch("/api/documents/{document_id}")
def api_save_document(document_id: str, payload: Annotated[dict, Body()]):
    document = save_document(document_id, payload)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.get("/api/assessments/{assessment_id}/reports/evidence.xlsx")
def api_evidence_report(assessment_id: str):
    if not get_assessment(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    return Response(
        evidence_report_xlsx(assessment_id),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=evidence_capture_report.xlsx"},
    )


@app.get("/api/assessments/{assessment_id}/reports/poam.xlsx")
def api_poam_report(assessment_id: str):
    if not get_assessment(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    return Response(
        poam_report_xlsx(assessment_id),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=poam_report.xlsx"},
    )


@app.get("/api/clients/{client_id}/exports/package.zip")
def api_export_package(client_id: str, assessment_id: str):
    path = export_platform_package(client_id, assessment_id)
    return FileResponse(path, filename=path.name, media_type="application/zip")
