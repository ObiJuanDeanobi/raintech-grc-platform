import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.database import Database
from api.framework import FRAMEWORK_ID, seed_framework
from api.storage import FileStorage, LocalFileStorage


def now() -> str:
    return datetime.now(UTC).isoformat()


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    framework_version_id: str = FRAMEWORK_ID


class DeterminationSave(BaseModel):
    status: str
    na_rationale: str = ""
    addressable_disposition: str | None = None
    disposition_reason: str = ""
    interview_observation: str = ""


class NoteSave(BaseModel):
    note: str


class EvidenceMappingCreate(BaseModel):
    artifact_id: str
    record_id: str
    rationale: str = ""


class PromptAnswerSave(BaseModel):
    answer: str


class PromptWorkingRecordSave(BaseModel):
    status: str
    note: str = ""
    na_rationale: str = ""
    interview_observation: str = ""


class PromptEvidenceMappingCreate(BaseModel):
    artifact_id: str
    prompt_id: str
    rationale: str = ""


class PromptPlacementSave(BaseModel):
    destination_record_id: str | None = None
    rule_citation: str = ""
    reason: str = Field(min_length=1)


class PromptMoveRejectionSave(BaseModel):
    proposed_record_id: str
    reason: str = Field(min_length=1)


def _row(row: Any) -> dict[str, Any]:
    return dict(row)


def _audit(
    connection: Any,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO audit_events(
            id, actor_id, action, entity_type, entity_id, details_json, created_at
        ) VALUES (?, 'johnathan', ?, ?, ?, ?, ?)
        """,
        (str(uuid4()), action, entity_type, entity_id, json.dumps(details), now()),
    )


def _record_or_404(connection: Any, assessment_id: str, record_id: str) -> Any:
    record = connection.execute(
        """
        SELECT framework_records.*
        FROM framework_records
        JOIN assessments
          ON assessments.framework_version_id = framework_records.framework_version_id
        WHERE assessments.id = ? AND framework_records.record_id = ?
        """,
        (assessment_id, record_id),
    ).fetchone()
    if record is None:
        raise HTTPException(status_code=404, detail="Assessment record not found")
    return record


def _framework_declarations(connection: Any, assessment_id: str) -> dict[str, Any]:
    framework = connection.execute(
        """
        SELECT framework_versions.declarations_json
        FROM framework_versions
        JOIN assessments ON assessments.framework_version_id = framework_versions.id
        WHERE assessments.id = ?
        """,
        (assessment_id,),
    ).fetchone()
    if framework is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return cast(dict[str, Any], json.loads(framework["declarations_json"]))


def _rollup_status(statuses: list[str], declarations: dict[str, Any]) -> str:
    if not statuses:
        return ""
    rule = declarations["rollup_rule"]
    for status in rule["precedence"]:
        if status in statuses:
            return cast(str, status)
    blank_status = cast(str, rule.get("blank_status", ""))
    if rule.get("blank_children_prevent_met", True) and blank_status in statuses:
        return blank_status
    if all(status in set(rule["satisfied_child_statuses"]) for status in statuses):
        return cast(str, rule["satisfied_rollup_status"])
    return blank_status


def _assessment_question_statuses(
    connection: Any,
    assessment_id: str,
    framework_version_id: str,
    record_id: str,
) -> list[str]:
    return [
        row["status"] or ""
        for row in connection.execute(
            """
            SELECT COALESCE(pa.status, '') AS status
            FROM framework_prompts fp
            LEFT JOIN prompt_answers pa
              ON pa.prompt_id = fp.prompt_id AND pa.assessment_id = ?
            LEFT JOIN prompt_placements pp
              ON pp.prompt_id = fp.prompt_id AND pp.assessment_id = ?
            WHERE fp.framework_version_id = ?
              AND fp.role = 'assessment_check'
              AND COALESCE(pp.destination_record_id, fp.original_record_id) = ?
              AND COALESCE(pp.placement_type, 'record') != 'context'
            ORDER BY fp.sort_order
            """,
            (assessment_id, assessment_id, framework_version_id, record_id),
        )
    ]


def _derived_input_statuses(
    connection: Any,
    assessment_id: str,
    record: Any,
) -> list[str]:
    statuses = _assessment_question_statuses(
        connection,
        assessment_id,
        record["framework_version_id"],
        record["record_id"],
    )
    children = connection.execute(
        """
        SELECT * FROM framework_records
        WHERE framework_version_id = ? AND parent_id = ?
        ORDER BY sort_order
        """,
        (record["framework_version_id"], record["record_id"]),
    ).fetchall()
    statuses.extend(_record_status(connection, assessment_id, child) for child in children)
    return statuses


def _record_status(connection: Any, assessment_id: str, record: Any) -> str:
    derived_inputs = _derived_input_statuses(connection, assessment_id, record)
    if derived_inputs:
        return _rollup_status(
            derived_inputs,
            _framework_declarations(connection, assessment_id),
        )
    if not record["carries_determination"]:
        return ""
    value = connection.execute(
        """
        SELECT status FROM determinations
        WHERE assessment_id = ? AND record_id = ?
        """,
        (assessment_id, record["record_id"]),
    ).fetchone()
    return cast(str, value["status"] if value is not None else "")


def _determination(connection: Any, assessment_id: str, record: Any) -> dict[str, Any]:
    value = connection.execute(
        """
        SELECT status, na_rationale, addressable_disposition, disposition_reason,
               interview_observation, updated_at
        FROM determinations WHERE assessment_id = ? AND record_id = ?
        """,
        (assessment_id, record["record_id"]),
    ).fetchone()
    result = (
        _row(value)
        if value is not None
        else {
            "status": "",
            "na_rationale": "",
            "addressable_disposition": None,
            "disposition_reason": "",
            "interview_observation": "",
            "updated_at": None,
        }
    )
    derived_inputs = _derived_input_statuses(connection, assessment_id, record)
    result["derived"] = bool(derived_inputs) or not record["carries_determination"]
    result["status"] = (
        _rollup_status(
            derived_inputs,
            _framework_declarations(connection, assessment_id),
        )
        if derived_inputs
        else result["status"]
    )
    return result


def _artifact_mapping_count(connection: Any, artifact_id: str) -> int:
    return cast(
        int,
        connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM evidence_mappings WHERE artifact_id = ?)
              + (SELECT COUNT(*) FROM prompt_evidence_mappings WHERE artifact_id = ?)
                AS count
            """,
            (artifact_id, artifact_id),
        ).fetchone()["count"],
    )


def _prompt_working_record(
    connection: Any,
    assessment_id: str,
    prompt: Any,
) -> dict[str, Any] | None:
    if prompt["role"] != "assessment_check":
        return None
    evidence = [
        {
            **_row(mapping),
            "shared_record_count": _artifact_mapping_count(connection, mapping["artifact_id"]),
        }
        for mapping in connection.execute(
            """
            SELECT pem.id AS mapping_id, pem.artifact_id, ea.name, ea.relative_path,
                   pem.rationale
            FROM prompt_evidence_mappings pem
            JOIN evidence_artifacts ea ON ea.id = pem.artifact_id
            WHERE pem.assessment_id = ? AND pem.prompt_id = ?
            ORDER BY pem.created_at
            """,
            (assessment_id, prompt["prompt_id"]),
        )
    ]
    return {
        "status": prompt["working_status"] or "",
        "note": prompt["answer"] or "",
        "na_rationale": prompt["working_na_rationale"] or "",
        "interview_observation": prompt["working_interview_observation"] or "",
        "updated_at": prompt["working_updated_at"],
        "evidence": evidence,
    }


def _record_summary(connection: Any, assessment_id: str, record: Any) -> dict[str, Any]:
    result = {
        "record_id": record["record_id"],
        "citation": record["citation"],
        "title": record["title"],
        "regulation_text": record["regulation_text"],
        "work_area": record["work_area"],
        "record_type": record["record_type"],
        "parent_id": record["parent_id"],
        "designation": record["designation"],
        "editable_determination": bool(record["carries_determination"])
        and not _derived_input_statuses(connection, assessment_id, record),
    }
    result["determination"] = _determination(connection, assessment_id, record)
    return result


def _prompt_or_404(connection: Any, assessment_id: str, prompt_id: str) -> Any:
    prompt = connection.execute(
        """
        SELECT fp.*, pa.answer, pa.status AS working_status,
               pa.na_rationale AS working_na_rationale,
               pa.interview_observation AS working_interview_observation,
               pa.updated_at AS working_updated_at,
               pp.placement_type, pp.destination_record_id,
               COALESCE(pp.destination_record_id, fp.original_record_id) AS current_record_id
        FROM framework_prompts fp
        JOIN assessments
          ON assessments.framework_version_id = fp.framework_version_id
        LEFT JOIN prompt_answers pa
          ON pa.prompt_id = fp.prompt_id AND pa.assessment_id = assessments.id
        LEFT JOIN prompt_placements pp
          ON pp.prompt_id = fp.prompt_id AND pp.assessment_id = assessments.id
        WHERE assessments.id = ? AND fp.prompt_id = ?
        """,
        (assessment_id, prompt_id),
    ).fetchone()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return prompt


def _prompts_for_record(
    connection: Any,
    assessment_id: str,
    framework_version_id: str,
    record_id: str | None,
) -> list[dict[str, Any]]:
    prompt_rows = connection.execute(
        """
        SELECT fp.*, pa.answer, pa.status AS working_status,
               pa.na_rationale AS working_na_rationale,
               pa.interview_observation AS working_interview_observation,
               pa.updated_at AS working_updated_at,
               pp.placement_type, pp.destination_record_id,
               pp.rule_citation, pp.reason AS placement_reason,
               origin.citation AS origin_citation, origin.title AS origin_title,
               COALESCE(pp.destination_record_id, fp.original_record_id) AS current_record_id
        FROM framework_prompts fp
        LEFT JOIN prompt_answers pa
          ON pa.prompt_id = fp.prompt_id AND pa.assessment_id = ?
        LEFT JOIN prompt_placements pp
          ON pp.prompt_id = fp.prompt_id AND pp.assessment_id = ?
        LEFT JOIN framework_records origin
          ON origin.framework_version_id = fp.framework_version_id
         AND origin.record_id = fp.original_record_id
        WHERE fp.framework_version_id = ?
          AND (
            (? IS NULL AND pp.placement_type = 'context')
            OR
            (? IS NOT NULL
             AND COALESCE(pp.destination_record_id, fp.original_record_id) = ?
             AND COALESCE(pp.placement_type, 'record') != 'context')
          )
        ORDER BY fp.sort_order
        """,
        (
            assessment_id,
            assessment_id,
            framework_version_id,
            record_id,
            record_id,
            record_id,
        ),
    ).fetchall()
    prompts: list[dict[str, Any]] = []
    for prompt in prompt_rows:
        item: dict[str, Any] = {
            "id": prompt["prompt_id"],
            "text": prompt["prompt_text"],
            "source": prompt["source"],
            "source_detail": prompt["source_detail"],
            "cfr_paragraph": prompt["cfr_paragraph"],
            "group": prompt["group_name"],
            "role": prompt["role"],
            "role_reason": prompt["role_reason"],
            "render_checkbox": prompt["role"] == "assessment_check",
            "answer": prompt["answer"] or "",
            "record_id": prompt["current_record_id"],
            "working_record": _prompt_working_record(connection, assessment_id, prompt),
            "moved_from": None,
            "placement": None,
        }
        if prompt["placement_type"] in {"record", "context"}:
            item["moved_from"] = {
                "record_id": prompt["original_record_id"],
                "citation": prompt["origin_citation"],
                "title": prompt["origin_title"],
            }
            item["placement"] = {
                "rule_citation": prompt["rule_citation"],
                "reason": prompt["placement_reason"],
            }
        prompts.append(item)
    return prompts


def _record_detail(connection: Any, assessment_id: str, record_id: str) -> dict[str, Any]:
    record = _record_or_404(connection, assessment_id, record_id)
    assessment = connection.execute(
        "SELECT framework_version_id FROM assessments WHERE id = ?",
        (assessment_id,),
    ).fetchone()
    parent = None
    if record["parent_id"]:
        parent_row = connection.execute(
            """
            SELECT * FROM framework_records
            WHERE framework_version_id = ? AND record_id = ?
            """,
            (assessment["framework_version_id"], record["parent_id"]),
        ).fetchone()
        parent = _record_summary(connection, assessment_id, parent_row)
        parent["prompts_collapsed_by_default"] = True

    children = [
        _record_summary(connection, assessment_id, child)
        for child in connection.execute(
            """
            SELECT * FROM framework_records
            WHERE framework_version_id = ? AND parent_id = ? ORDER BY sort_order
            """,
            (assessment["framework_version_id"], record_id),
        )
    ]
    prompts = _prompts_for_record(
        connection,
        assessment_id,
        assessment["framework_version_id"],
        record_id,
    )
    parent_prompts = (
        _prompts_for_record(
            connection,
            assessment_id,
            assessment["framework_version_id"],
            record["parent_id"],
        )
        if record["parent_id"]
        else []
    )
    context_prompts = _prompts_for_record(
        connection,
        assessment_id,
        assessment["framework_version_id"],
        None,
    )

    note = connection.execute(
        "SELECT note FROM record_notes WHERE assessment_id = ? AND record_id = ?",
        (assessment_id, record_id),
    ).fetchone()
    evidence = [
        {
            **_row(mapping),
            "shared_record_count": _artifact_mapping_count(connection, mapping["artifact_id"]),
        }
        for mapping in connection.execute(
            """
            SELECT em.id AS mapping_id, em.artifact_id, ea.name, ea.relative_path,
                   em.rationale
            FROM evidence_mappings em
            JOIN evidence_artifacts ea ON ea.id = em.artifact_id
            WHERE em.assessment_id = ? AND em.record_id = ?
            ORDER BY em.created_at
            """,
            (assessment_id, record_id),
        )
    ]
    position = None
    if record["carries_determination"]:
        work_ids = [
            row["record_id"]
            for row in connection.execute(
                """
                SELECT record_id FROM framework_records
                WHERE framework_version_id = ? AND carries_determination = 1
                ORDER BY sort_order
                """,
                (assessment["framework_version_id"],),
            )
        ]
        current = work_ids.index(record_id)
        position = {
            "current": current + 1,
            "total": len(work_ids),
            "previous_record_id": work_ids[current - 1] if current > 0 else None,
            "next_record_id": work_ids[current + 1] if current + 1 < len(work_ids) else None,
        }
    summary = _record_summary(connection, assessment_id, record)
    determination = summary.pop("determination")
    return {
        "record": summary,
        "determination": determination,
        "parent": parent,
        "parent_prompts": parent_prompts,
        "context_prompts": context_prompts,
        "children": children,
        "prompts": prompts,
        "note": note["note"] if note else "",
        "evidence": evidence,
        "position": position,
    }


def create_app(
    database_path: Path | None = None,
    storage_path: Path | None = None,
    repository_root: Path | None = None,
) -> FastAPI:
    root = repository_root or Path(__file__).resolve().parents[1]
    database = Database(database_path or root / "data" / "workspace.db")
    managed_storage = storage_path or root / "data" / "files"
    storage: FileStorage = LocalFileStorage(managed_storage)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database.migrate()
        managed_storage.mkdir(parents=True, exist_ok=True)
        seed_framework(database, root)
        app.state.database = database
        app.state.file_storage = storage
        yield

    app = FastAPI(title="RainTech GRC API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def db(request: Request) -> Database:
        return cast(Database, request.app.state.database)

    def files(request: Request) -> FileStorage:
        return cast(FileStorage, request.app.state.file_storage)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/clients")
    def list_clients(database: Annotated[Database, Depends(db)]) -> list[dict[str, Any]]:
        with database.connect() as connection:
            clients = [
                _row(row) for row in connection.execute("SELECT * FROM clients ORDER BY name")
            ]
            for item in clients:
                item["projects"] = [
                    _row(row)
                    for row in connection.execute(
                        "SELECT * FROM projects WHERE client_id = ? ORDER BY created_at",
                        (item["id"],),
                    )
                ]
            return clients

    @app.post("/api/clients", status_code=201)
    def create_client(
        payload: ClientCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        item = {"id": str(uuid4()), "name": payload.name.strip(), "created_at": now()}
        with database.connect() as connection:
            connection.execute(
                "INSERT INTO clients(id, name, created_at) VALUES (?, ?, ?)",
                (item["id"], item["name"], item["created_at"]),
            )
            _audit(connection, "client.created", "client", item["id"], {"name": item["name"]})
        return item

    @app.post("/api/clients/{client_id}/projects", status_code=201)
    def create_project(
        client_id: str,
        payload: ProjectCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        item = {
            "id": str(uuid4()),
            "client_id": client_id,
            "name": payload.name.strip(),
            "framework_version_id": payload.framework_version_id,
            "created_at": now(),
        }
        assessment_id = str(uuid4())
        with database.connect() as connection:
            if (
                connection.execute(
                    "SELECT id FROM framework_versions WHERE id = ?",
                    (payload.framework_version_id,),
                ).fetchone()
                is None
            ):
                raise HTTPException(status_code=422, detail="Unknown framework version")
            if (
                connection.execute("SELECT id FROM clients WHERE id = ?", (client_id,)).fetchone()
                is None
            ):
                raise HTTPException(status_code=404, detail="Client not found")
            connection.execute(
                """
                INSERT INTO projects(
                    id, client_id, name, framework_version_id, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                tuple(item.values()),
            )
            connection.execute(
                """
                INSERT INTO assessments(id, project_id, framework_version_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (assessment_id, item["id"], payload.framework_version_id, now()),
            )
            _audit(connection, "project.created", "project", item["id"], {"name": item["name"]})
            _audit(
                connection,
                "assessment.created",
                "assessment",
                assessment_id,
                {"framework_version_id": payload.framework_version_id},
            )
        return item

    @app.get("/api/projects/{project_id}/assessment")
    def get_assessment(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            assessment = connection.execute(
                """
                SELECT assessments.*, projects.name AS project_name,
                       clients.id AS client_id, clients.name AS client_name
                FROM assessments
                JOIN projects ON projects.id = assessments.project_id
                JOIN clients ON clients.id = projects.client_id
                WHERE projects.id = ?
                """,
                (project_id,),
            ).fetchone()
            if assessment is None:
                raise HTTPException(status_code=404, detail="Assessment not found")
            framework = connection.execute(
                "SELECT * FROM framework_versions WHERE id = ?",
                (assessment["framework_version_id"],),
            ).fetchone()
            work_list = []
            for row in connection.execute(
                """
                SELECT * FROM framework_records
                WHERE framework_version_id = ? AND carries_determination = 1
                ORDER BY sort_order
                """,
                (assessment["framework_version_id"],),
            ):
                item = _record_summary(connection, assessment["id"], row)
                item.pop("regulation_text")
                work_list.append(item)
            record_index = [
                {
                    **_row(row),
                    "editable_determination": bool(row["carries_determination"])
                    and not _derived_input_statuses(connection, assessment["id"], row),
                }
                for row in connection.execute(
                    """
                    SELECT * FROM framework_records
                    WHERE framework_version_id = ?
                    ORDER BY sort_order
                    """,
                    (assessment["framework_version_id"],),
                )
            ]
            return {
                "id": assessment["id"],
                "project": {
                    "id": assessment["project_id"],
                    "name": assessment["project_name"],
                    "client_id": assessment["client_id"],
                    "client_name": assessment["client_name"],
                },
                "framework": {
                    "id": framework["id"],
                    "name": framework["name"],
                    "record_count": framework["record_count"],
                    "prompt_count": framework["prompt_count"],
                    "determination_record_count": len(work_list),
                    "declarations": json.loads(framework["declarations_json"]),
                },
                "work_list": work_list,
                "record_index": record_index,
            }

    @app.get("/api/assessments/{assessment_id}/records/{record_id}")
    def get_record(
        assessment_id: str,
        record_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            return _record_detail(connection, assessment_id, record_id)

    @app.put("/api/assessments/{assessment_id}/determinations/{record_id}")
    def save_determination(
        assessment_id: str,
        record_id: str,
        payload: DeterminationSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            record = _record_or_404(connection, assessment_id, record_id)
            declarations = _framework_declarations(connection, assessment_id)
            if payload.status not in set(declarations["status_set"]):
                raise HTTPException(status_code=422, detail="Unknown determination status")
            if not record["carries_determination"]:
                raise HTTPException(
                    status_code=422,
                    detail="Parent status is derived and cannot be edited",
                )
            derived_inputs = _derived_input_statuses(connection, assessment_id, record)
            if derived_inputs:
                derived_status = _rollup_status(derived_inputs, declarations)
                if payload.status != derived_status:
                    raise HTTPException(
                        status_code=422,
                        detail="Record status derives from its assessment questions",
                    )
            if payload.status == "N/A" and not payload.na_rationale.strip():
                raise HTTPException(status_code=422, detail="N/A requires a rationale")
            designation_rule = declarations.get("designation_rules", {}).get(
                record["designation"]
            )
            if designation_rule:
                if payload.addressable_disposition not in set(designation_rule["dispositions"]):
                    raise HTTPException(
                        status_code=422,
                        detail="Addressable specifications require a disposition",
                    )
                if (
                    payload.addressable_disposition
                    in set(designation_rule["reason_required_for"])
                    and not payload.disposition_reason.strip()
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="This addressable disposition requires reasoning",
                    )
            if (
                payload.status == "Met"
                and not derived_inputs
                and not payload.interview_observation.strip()
            ):
                evidence = connection.execute(
                    """
                    SELECT id FROM evidence_mappings
                    WHERE assessment_id = ? AND record_id = ? LIMIT 1
                    """,
                    (assessment_id, record_id),
                ).fetchone()
                if evidence is None:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Met requires mapped evidence or a documented interview/observation"
                        ),
                    )
            saved_at = now()
            connection.execute(
                """
                INSERT INTO determinations(
                    assessment_id, record_id, status, na_rationale,
                    addressable_disposition, disposition_reason,
                    interview_observation, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assessment_id, record_id) DO UPDATE SET
                    status = excluded.status,
                    na_rationale = excluded.na_rationale,
                    addressable_disposition = excluded.addressable_disposition,
                    disposition_reason = excluded.disposition_reason,
                    interview_observation = excluded.interview_observation,
                    updated_at = excluded.updated_at
                """,
                (
                    assessment_id,
                    record_id,
                    payload.status,
                    payload.na_rationale.strip(),
                    payload.addressable_disposition,
                    payload.disposition_reason.strip(),
                    payload.interview_observation.strip(),
                    saved_at,
                ),
            )
            _audit(
                connection,
                "determination.saved",
                "determination",
                f"{assessment_id}:{record_id}",
                {
                    "assessment_id": assessment_id,
                    "record_id": record_id,
                    "status": payload.status,
                },
            )
            saved = _record_detail(connection, assessment_id, record_id)["determination"]
            return cast(dict[str, Any], saved)

    @app.put("/api/assessments/{assessment_id}/records/{record_id}/note")
    def save_note(
        assessment_id: str,
        record_id: str,
        payload: NoteSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, str]:
        with database.connect() as connection:
            _record_or_404(connection, assessment_id, record_id)
            saved_at = now()
            connection.execute(
                """
                INSERT INTO record_notes(assessment_id, record_id, note, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(assessment_id, record_id) DO UPDATE SET
                    note = excluded.note, updated_at = excluded.updated_at
                """,
                (assessment_id, record_id, payload.note, saved_at),
            )
            _audit(
                connection,
                "record.note_saved",
                "record_note",
                f"{assessment_id}:{record_id}",
                {"assessment_id": assessment_id, "record_id": record_id},
            )
        return {"note": payload.note, "updated_at": saved_at}

    @app.post("/api/projects/{project_id}/evidence", status_code=201)
    async def create_evidence(
        project_id: str,
        file: Annotated[UploadFile, File()],
        database: Annotated[Database, Depends(db)],
        file_storage: Annotated[FileStorage, Depends(files)],
    ) -> dict[str, Any]:
        artifact_id = str(uuid4())
        content = await file.read()
        if not file.filename:
            raise HTTPException(status_code=422, detail="Evidence filename is required")
        with database.connect() as connection:
            if (
                connection.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
                is None
            ):
                raise HTTPException(status_code=404, detail="Project not found")
            relative_path = file_storage.save(project_id, artifact_id, file.filename, content)
            created_at = now()
            connection.execute(
                """
                INSERT INTO evidence_artifacts(id, project_id, name, relative_path, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (artifact_id, project_id, file.filename, relative_path, created_at),
            )
            _audit(
                connection,
                "evidence.created",
                "evidence_artifact",
                artifact_id,
                {"project_id": project_id, "name": file.filename},
            )
        return {
            "id": artifact_id,
            "project_id": project_id,
            "name": file.filename,
            "relative_path": relative_path,
            "created_at": created_at,
        }

    @app.get("/api/projects/{project_id}/evidence")
    def list_evidence(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            return [
                {
                    **_row(row),
                    "shared_record_count": _artifact_mapping_count(connection, row["id"]),
                }
                for row in connection.execute(
                    "SELECT * FROM evidence_artifacts WHERE project_id = ? ORDER BY created_at",
                    (project_id,),
                )
            ]

    @app.post("/api/assessments/{assessment_id}/evidence-mappings", status_code=201)
    def create_mapping(
        assessment_id: str,
        payload: EvidenceMappingCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        mapping_id = str(uuid4())
        with database.connect() as connection:
            _record_or_404(connection, assessment_id, payload.record_id)
            artifact = connection.execute(
                """
                SELECT ea.*
                FROM evidence_artifacts ea
                JOIN projects ON projects.id = ea.project_id
                JOIN assessments ON assessments.project_id = projects.id
                WHERE assessments.id = ? AND ea.id = ?
                """,
                (assessment_id, payload.artifact_id),
            ).fetchone()
            if artifact is None:
                raise HTTPException(status_code=404, detail="Evidence artifact not found")
            try:
                connection.execute(
                    """
                    INSERT INTO evidence_mappings(
                        id, artifact_id, assessment_id, record_id, rationale, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mapping_id,
                        payload.artifact_id,
                        assessment_id,
                        payload.record_id,
                        payload.rationale.strip(),
                        now(),
                    ),
                )
            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    raise HTTPException(
                        status_code=409,
                        detail="Evidence is already mapped to this record",
                    ) from error
                raise
            _audit(
                connection,
                "evidence.mapped",
                "evidence_mapping",
                mapping_id,
                {
                    "assessment_id": assessment_id,
                    "record_id": payload.record_id,
                    "artifact_id": payload.artifact_id,
                },
            )
            shared_count = _artifact_mapping_count(connection, payload.artifact_id)
        return {
            "id": mapping_id,
            "artifact_id": payload.artifact_id,
            "record_id": payload.record_id,
            "rationale": payload.rationale.strip(),
            "shared_record_count": shared_count,
        }

    @app.delete("/api/assessments/{assessment_id}/evidence-mappings/{mapping_id}")
    def delete_mapping(
        assessment_id: str,
        mapping_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, bool]:
        with database.connect() as connection:
            mapping = connection.execute(
                """
                SELECT * FROM evidence_mappings WHERE assessment_id = ? AND id = ?
                """,
                (assessment_id, mapping_id),
            ).fetchone()
            if mapping is None:
                raise HTTPException(status_code=404, detail="Evidence mapping not found")
            determination = connection.execute(
                """
                SELECT status, interview_observation
                FROM determinations
                WHERE assessment_id = ? AND record_id = ?
                """,
                (assessment_id, mapping["record_id"]),
            ).fetchone()
            mapping_count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM evidence_mappings
                WHERE assessment_id = ? AND record_id = ?
                """,
                (assessment_id, mapping["record_id"]),
            ).fetchone()["count"]
            if (
                determination
                and determination["status"] == "Met"
                and not determination["interview_observation"].strip()
                and mapping_count == 1
            ):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "This is the last evidence supporting a Met determination. "
                        "Change the determination or document an interview before unmapping it."
                    ),
                )
            connection.execute("DELETE FROM evidence_mappings WHERE id = ?", (mapping_id,))
            _audit(
                connection,
                "evidence.unmapped",
                "evidence_mapping",
                mapping_id,
                {
                    "assessment_id": assessment_id,
                    "record_id": mapping["record_id"],
                    "artifact_id": mapping["artifact_id"],
                },
            )
        return {"deleted": True}

    @app.put("/api/assessments/{assessment_id}/prompts/{prompt_id}/working-record")
    def save_prompt_working_record(
        assessment_id: str,
        prompt_id: str,
        payload: PromptWorkingRecordSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            prompt = _prompt_or_404(connection, assessment_id, prompt_id)
            if prompt["role"] != "assessment_check" or prompt["placement_type"] == "context":
                raise HTTPException(
                    status_code=422,
                    detail="Guidance-only questions do not carry a working-record status",
                )
            declarations = _framework_declarations(connection, assessment_id)
            if payload.status not in set(declarations["status_set"]):
                raise HTTPException(status_code=422, detail="Unknown question status")
            if payload.status == "N/A" and not payload.na_rationale.strip():
                raise HTTPException(status_code=422, detail="N/A requires a rationale")
            record = _record_or_404(connection, assessment_id, prompt["current_record_id"])
            designation_rule = declarations.get("designation_rules", {}).get(
                record["designation"]
            )
            if designation_rule and payload.status:
                disposition = connection.execute(
                    """
                    SELECT addressable_disposition, disposition_reason
                    FROM determinations
                    WHERE assessment_id = ? AND record_id = ?
                    """,
                    (assessment_id, record["record_id"]),
                ).fetchone()
                if (
                    disposition is None
                    or disposition["addressable_disposition"]
                    not in set(designation_rule["dispositions"])
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="Addressable specifications require a disposition",
                    )
                if (
                    disposition["addressable_disposition"]
                    in set(designation_rule["reason_required_for"])
                    and not disposition["disposition_reason"].strip()
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="This addressable disposition requires reasoning",
                    )
            if payload.status == "Met" and not payload.interview_observation.strip():
                evidence = connection.execute(
                    """
                    SELECT id FROM prompt_evidence_mappings
                    WHERE assessment_id = ? AND prompt_id = ? LIMIT 1
                    """,
                    (assessment_id, prompt_id),
                ).fetchone()
                if evidence is None:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Met requires mapped evidence or a documented interview/observation"
                        ),
                    )
            saved_at = now()
            connection.execute(
                """
                INSERT INTO prompt_answers(
                    assessment_id, prompt_id, answer, status, na_rationale,
                    interview_observation, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assessment_id, prompt_id) DO UPDATE SET
                    answer = excluded.answer,
                    status = excluded.status,
                    na_rationale = excluded.na_rationale,
                    interview_observation = excluded.interview_observation,
                    updated_at = excluded.updated_at
                """,
                (
                    assessment_id,
                    prompt_id,
                    payload.note,
                    payload.status,
                    payload.na_rationale.strip(),
                    payload.interview_observation.strip(),
                    saved_at,
                ),
            )
            _audit(
                connection,
                "prompt.working_record_saved",
                "prompt_working_record",
                f"{assessment_id}:{prompt_id}",
                {
                    "assessment_id": assessment_id,
                    "prompt_id": prompt_id,
                    "status": payload.status,
                },
            )
            saved_prompt = _prompt_or_404(connection, assessment_id, prompt_id)
            saved = _prompt_working_record(connection, assessment_id, saved_prompt)
            return cast(dict[str, Any], saved)

    @app.post(
        "/api/assessments/{assessment_id}/prompt-evidence-mappings",
        status_code=201,
    )
    def create_prompt_mapping(
        assessment_id: str,
        payload: PromptEvidenceMappingCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        mapping_id = str(uuid4())
        with database.connect() as connection:
            prompt = _prompt_or_404(connection, assessment_id, payload.prompt_id)
            if prompt["role"] != "assessment_check" or prompt["placement_type"] == "context":
                raise HTTPException(
                    status_code=422,
                    detail="Evidence can only map to an assessable question",
                )
            artifact = connection.execute(
                """
                SELECT ea.*
                FROM evidence_artifacts ea
                JOIN projects ON projects.id = ea.project_id
                JOIN assessments ON assessments.project_id = projects.id
                WHERE assessments.id = ? AND ea.id = ?
                """,
                (assessment_id, payload.artifact_id),
            ).fetchone()
            if artifact is None:
                raise HTTPException(status_code=404, detail="Evidence artifact not found")
            try:
                connection.execute(
                    """
                    INSERT INTO prompt_evidence_mappings(
                        id, artifact_id, assessment_id, prompt_id, rationale, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mapping_id,
                        payload.artifact_id,
                        assessment_id,
                        payload.prompt_id,
                        payload.rationale.strip(),
                        now(),
                    ),
                )
            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    raise HTTPException(
                        status_code=409,
                        detail="Evidence is already mapped to this question",
                    ) from error
                raise
            _audit(
                connection,
                "evidence.mapped_to_prompt",
                "prompt_evidence_mapping",
                mapping_id,
                {
                    "assessment_id": assessment_id,
                    "prompt_id": payload.prompt_id,
                    "artifact_id": payload.artifact_id,
                },
            )
            shared_count = _artifact_mapping_count(connection, payload.artifact_id)
        return {
            "id": mapping_id,
            "artifact_id": payload.artifact_id,
            "prompt_id": payload.prompt_id,
            "rationale": payload.rationale.strip(),
            "shared_record_count": shared_count,
        }

    @app.delete(
        "/api/assessments/{assessment_id}/prompt-evidence-mappings/{mapping_id}"
    )
    def delete_prompt_mapping(
        assessment_id: str,
        mapping_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, bool]:
        with database.connect() as connection:
            mapping = connection.execute(
                """
                SELECT * FROM prompt_evidence_mappings
                WHERE assessment_id = ? AND id = ?
                """,
                (assessment_id, mapping_id),
            ).fetchone()
            if mapping is None:
                raise HTTPException(status_code=404, detail="Evidence mapping not found")
            working_record = connection.execute(
                """
                SELECT status, interview_observation FROM prompt_answers
                WHERE assessment_id = ? AND prompt_id = ?
                """,
                (assessment_id, mapping["prompt_id"]),
            ).fetchone()
            mapping_count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM prompt_evidence_mappings
                WHERE assessment_id = ? AND prompt_id = ?
                """,
                (assessment_id, mapping["prompt_id"]),
            ).fetchone()["count"]
            if (
                working_record
                and working_record["status"] == "Met"
                and not working_record["interview_observation"].strip()
                and mapping_count == 1
            ):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "This is the last evidence supporting a Met question. "
                        "Change the status or document an interview before unmapping it."
                    ),
                )
            connection.execute(
                "DELETE FROM prompt_evidence_mappings WHERE id = ?", (mapping_id,)
            )
            _audit(
                connection,
                "evidence.unmapped_from_prompt",
                "prompt_evidence_mapping",
                mapping_id,
                {
                    "assessment_id": assessment_id,
                    "prompt_id": mapping["prompt_id"],
                    "artifact_id": mapping["artifact_id"],
                },
            )
        return {"deleted": True}

    @app.put("/api/assessments/{assessment_id}/prompts/{prompt_id}/answer")
    def save_prompt_answer(
        assessment_id: str,
        prompt_id: str,
        payload: PromptAnswerSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, str]:
        with database.connect() as connection:
            prompt = connection.execute(
                """
                SELECT fp.prompt_id
                FROM framework_prompts fp
                JOIN assessments
                  ON assessments.framework_version_id = fp.framework_version_id
                WHERE assessments.id = ? AND fp.prompt_id = ?
                """,
                (assessment_id, prompt_id),
            ).fetchone()
            if prompt is None:
                raise HTTPException(status_code=404, detail="Prompt not found")
            saved_at = now()
            connection.execute(
                """
                INSERT INTO prompt_answers(assessment_id, prompt_id, answer, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(assessment_id, prompt_id) DO UPDATE SET
                    answer = excluded.answer, updated_at = excluded.updated_at
                """,
                (assessment_id, prompt_id, payload.answer, saved_at),
            )
            _audit(
                connection,
                "prompt.answer_saved",
                "prompt_answer",
                f"{assessment_id}:{prompt_id}",
                {"assessment_id": assessment_id, "prompt_id": prompt_id},
            )
        return {"answer": payload.answer, "updated_at": saved_at}

    @app.put("/api/assessments/{assessment_id}/prompts/{prompt_id}/placement")
    def save_prompt_placement(
        assessment_id: str,
        prompt_id: str,
        payload: PromptPlacementSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        placement_type = "record" if payload.destination_record_id else "context"
        if placement_type == "record" and not payload.rule_citation.strip():
            raise HTTPException(
                status_code=422,
                detail="Moving a question to a record requires the rule it tests",
            )
        with database.connect() as connection:
            prompt = connection.execute(
                """
                SELECT fp.*
                FROM framework_prompts fp
                JOIN assessments
                  ON assessments.framework_version_id = fp.framework_version_id
                WHERE assessments.id = ? AND fp.prompt_id = ?
                """,
                (assessment_id, prompt_id),
            ).fetchone()
            if prompt is None:
                raise HTTPException(status_code=404, detail="Prompt not found")
            if payload.destination_record_id:
                _record_or_404(connection, assessment_id, payload.destination_record_id)
            created_at = now()
            connection.execute(
                """
                INSERT INTO prompt_placements(
                    assessment_id, prompt_id, placement_type, destination_record_id,
                    rule_citation, reason, actor_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'johnathan', ?)
                ON CONFLICT(assessment_id, prompt_id) DO UPDATE SET
                    placement_type = excluded.placement_type,
                    destination_record_id = excluded.destination_record_id,
                    rule_citation = excluded.rule_citation,
                    reason = excluded.reason,
                    actor_id = excluded.actor_id,
                    created_at = excluded.created_at
                """,
                (
                    assessment_id,
                    prompt_id,
                    placement_type,
                    payload.destination_record_id,
                    payload.rule_citation.strip(),
                    payload.reason.strip(),
                    created_at,
                ),
            )
            _audit(
                connection,
                "prompt.placement_saved",
                "prompt_placement",
                f"{assessment_id}:{prompt_id}",
                {
                    "assessment_id": assessment_id,
                    "prompt_id": prompt_id,
                    "original_record_id": prompt["original_record_id"],
                    "destination_record_id": payload.destination_record_id,
                    "placement_type": placement_type,
                },
            )
        return {
            "prompt_id": prompt_id,
            "placement_type": placement_type,
            "destination_record_id": payload.destination_record_id,
            "rule_citation": payload.rule_citation.strip(),
            "reason": payload.reason.strip(),
            "actor": {"id": "johnathan", "display_name": "Johnathan"},
            "created_at": created_at,
        }

    @app.get("/api/assessments/{assessment_id}/prompts/{prompt_id}/rejections")
    def list_prompt_move_rejections(
        assessment_id: str,
        prompt_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            return [
                _row(row)
                for row in connection.execute(
                    """
                    SELECT proposed_record_id, reason, actor_id, created_at
                    FROM prompt_move_rejections
                    WHERE assessment_id = ? AND prompt_id = ?
                    ORDER BY created_at
                    """,
                    (assessment_id, prompt_id),
                )
            ]

    @app.post(
        "/api/assessments/{assessment_id}/prompts/{prompt_id}/rejections",
        status_code=201,
    )
    def reject_prompt_move(
        assessment_id: str,
        prompt_id: str,
        payload: PromptMoveRejectionSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            prompt = connection.execute(
                """
                SELECT fp.prompt_id
                FROM framework_prompts fp
                JOIN assessments
                  ON assessments.framework_version_id = fp.framework_version_id
                WHERE assessments.id = ? AND fp.prompt_id = ?
                """,
                (assessment_id, prompt_id),
            ).fetchone()
            if prompt is None:
                raise HTTPException(status_code=404, detail="Prompt not found")
            _record_or_404(connection, assessment_id, payload.proposed_record_id)
            created_at = now()
            connection.execute(
                """
                INSERT INTO prompt_move_rejections(
                    assessment_id, prompt_id, proposed_record_id, reason, actor_id, created_at
                ) VALUES (?, ?, ?, ?, 'johnathan', ?)
                ON CONFLICT(assessment_id, prompt_id, proposed_record_id) DO UPDATE SET
                    reason = excluded.reason,
                    actor_id = excluded.actor_id,
                    created_at = excluded.created_at
                """,
                (
                    assessment_id,
                    prompt_id,
                    payload.proposed_record_id,
                    payload.reason.strip(),
                    created_at,
                ),
            )
            _audit(
                connection,
                "prompt.move_rejected",
                "prompt_move_rejection",
                f"{assessment_id}:{prompt_id}:{payload.proposed_record_id}",
                {
                    "assessment_id": assessment_id,
                    "prompt_id": prompt_id,
                    "proposed_record_id": payload.proposed_record_id,
                },
            )
        return {
            "prompt_id": prompt_id,
            "proposed_record_id": payload.proposed_record_id,
            "reason": payload.reason.strip(),
            "actor_id": "johnathan",
            "created_at": created_at,
        }

    @app.get("/api/assessments/{assessment_id}/audit")
    def list_audit(
        assessment_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            if (
                connection.execute(
                    "SELECT id FROM assessments WHERE id = ?", (assessment_id,)
                ).fetchone()
                is None
            ):
                raise HTTPException(status_code=404, detail="Assessment not found")
            rows = connection.execute(
                """
                SELECT ae.*, ua.display_name
                FROM audit_events ae
                JOIN user_accounts ua ON ua.id = ae.actor_id
                WHERE ae.entity_id = ? OR ae.details_json LIKE ?
                ORDER BY ae.created_at
                """,
                (assessment_id, f"%{assessment_id}%"),
            )
            return [
                {
                    "id": row["id"],
                    "actor": {
                        "id": row["actor_id"],
                        "display_name": row["display_name"],
                    },
                    "action": row["action"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "details": json.loads(row["details_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    return app


app = create_app()
