import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from api.database import Database, profile_snapshot_revision
from api.framework import FRAMEWORK_ID, seed_framework
from api.risk import RiskScore, score_risk
from api.storage import FileStorage, LocalFileStorage
from api.close import fieldwork_ready


def now() -> str:
    return datetime.now(UTC).isoformat()


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    framework_version_id: str = FRAMEWORK_ID


class ProfileReadinessTransitionCreate(BaseModel):
    next_state: str
    decision_note: str = Field(min_length=1, max_length=1000)
    unresolved_required_fields: list[str] = Field(default_factory=list)
    follow_up_work: str = Field(default="", max_length=2000)
    reviewed_by: str = Field(default="", max_length=200)
    approval_evidence: str = Field(default="", max_length=2000)


class DeterminationSave(BaseModel):
    status: str
    na_rationale: str = ""
    addressable_disposition: str | None = None
    disposition_reason: str = ""
    interview_observation: str = ""


class ReconciliationSave(BaseModel):
    actor_id: str = "johnathan"
    outcome: str
    finding_id: str | None = None
    corrective_action_id: str | None = None
    rationale: str = ""
    title: str = ""
    description: str = ""
    action_title: str = ""
    action_description: str = ""


class CorrectiveActionStateSave(BaseModel):
    actor_id: str = "johnathan"
    state: str


class ValidationSave(BaseModel):
    actor_id: str = "johnathan"
    outcome: str
    notes: str = ""


class NoteSave(BaseModel):
    note: str


class EvidenceMappingCreate(BaseModel):
    artifact_id: str
    record_id: str
    rationale: str = Field(min_length=1)


class ProfileValueSave(BaseModel):
    section: str = Field(min_length=1, max_length=100)
    field_key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(max_length=10000)
    source: str = Field(min_length=1, max_length=1000)
    reviewer: str = Field(min_length=1, max_length=200)
    last_reviewed_at: str


class ProfileItemSave(BaseModel):
    client_key: str = Field(min_length=1, max_length=200)
    item_type: str
    environment_item_key: str | None = None
    values: list[ProfileValueSave] = Field(min_length=1)


class ProfileVersionSave(BaseModel):
    actor_id: str = "johnathan"
    expected_revision: str
    values: list[ProfileValueSave] = Field(default_factory=list)
    items: list[ProfileItemSave] = Field(default_factory=list)


class ProfileVersionCreate(BaseModel):
    actor_id: str = "johnathan"
    base_version_id: str | None = None


class ProfileLifecycleCreate(BaseModel):
    actor_id: str = "johnathan"
    expected_revision: str
    status: str
    reviewer: str = Field(default="", max_length=200)


class ProfileEvidenceMappingCreate(BaseModel):
    actor_id: str = "johnathan"
    expected_revision: str
    artifact_id: str
    evidence_version_id: str
    target_key: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=2000)


class ProfileEvidenceMappingUpdate(BaseModel):
    actor_id: str = "johnathan"
    expected_revision: str
    target_key: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=2000)


class PromptAnswerSave(BaseModel):
    answer: str


class SRAScopeSave(BaseModel):
    actor_id: str = "johnathan"
    profile_version_id: str
    scope_type: str
    target_key: str
    included: bool = True
    exclusion_rationale: str = ""
    reviewed_by: str = Field(default="Johnathan", min_length=1, max_length=200)

    @field_validator("reviewed_by")
    @classmethod
    def reviewed_by_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewed_by cannot be blank")
        return value.strip()


class RiskSave(BaseModel):
    actor_id: str = "johnathan"
    profile_version_id: str
    assessment_id: str
    title: str = Field(min_length=1, max_length=300)
    threat: str = Field(min_length=1, max_length=4000)
    vulnerability: str = Field(min_length=1, max_length=4000)
    cia_impact: str = Field(min_length=1, max_length=4000)
    safeguards: str = Field(min_length=1, max_length=4000)
    corrective_action: str = ""
    treatment: str = "corrective_action"
    owner: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=100)
    review_date: str | None = None
    inherent_likelihood: int = Field(ge=1, le=5)
    inherent_impact: int = Field(ge=1, le=5)
    residual_likelihood: int = Field(ge=1, le=5)
    residual_impact: int = Field(ge=1, le=5)
    acceptance_rationale: str = ""
    approver: str = ""
    approved_at: str | None = None
    reviewed_by: str = Field(min_length=1, max_length=200)
    reviewed_at: str

    @field_validator(
        "title",
        "threat",
        "vulnerability",
        "cia_impact",
        "safeguards",
        "owner",
        "status",
        "reviewed_by",
    )
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required risk text cannot be blank")
        return value.strip()

    @field_validator(
        "corrective_action",
        "treatment",
        "acceptance_rationale",
        "approver",
    )
    @classmethod
    def normalize_optional_text(cls, value: str) -> str:
        return value.strip()


class RiskEvidenceMappingCreate(BaseModel):
    actor_id: str = "johnathan"
    artifact_id: str
    evidence_version_id: str
    rationale: str = Field(min_length=1, max_length=2000)


def _row(row: Any) -> dict[str, Any]:
    return dict(row)


def _audit(
    connection: Any,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any],
    actor_id: str = "johnathan",
) -> None:
    connection.execute(
        """
        INSERT INTO audit_events(
            id, actor_id, action, entity_type, entity_id, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (str(uuid4()), actor_id, action, entity_type, entity_id, json.dumps(details), now()),
    )


def _project_or_404(connection: Any, project_id: str) -> Any:
    project = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _user_or_422(connection: Any, actor_id: str) -> Any:
    user = connection.execute("SELECT * FROM user_accounts WHERE id = ?", (actor_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=422, detail="Unknown Profile actor")
    return user


PROFILE_ITEM_TYPES = {
    "scope_item",
    "environment",
    "business_process",
    "location",
    "external_service",
    "person_role",
    "exclusion_constraint",
    "reference",
    "unknown_follow_up",
}
ENVIRONMENT_TYPES = {"cloud", "physical", "site", "network"}


def _profile_target_key(item: ProfileItemSave | None, field: ProfileValueSave) -> str:
    if item is None:
        return f"field:{field.section}:{field.field_key}"
    return f"item:{item.client_key}:{field.field_key}"


def _profile_target_or_404(
    connection: Any, project_id: str, version_id: str, target_key: str
) -> Any:
    targets = connection.execute(
        """
        SELECT field_values.id, field_values.profile_version_id
        FROM profile_field_values field_values
        JOIN profile_versions versions ON versions.id = field_values.profile_version_id
        LEFT JOIN profile_items items ON items.id = field_values.profile_item_id
        WHERE field_values.profile_version_id = ?
          AND (
            (
              field_values.profile_item_id IS NULL
              AND ? = 'field:' || field_values.section || ':' || field_values.field_key
            ) OR (
              field_values.profile_item_id IS NOT NULL
              AND ? = 'item:' || items.client_key || ':' || field_values.field_key
            )
          )
          AND versions.project_id = ?
        """,
        (version_id, target_key, target_key, project_id),
    ).fetchall()
    if len(targets) != 1:
        raise HTTPException(status_code=404, detail="Profile evidence target not found")
    return targets[0]


def _profile_mapping_destination_or_404(
    connection: Any, project_id: str, version_id: str, mapping_id: str
) -> Any:
    mapping = connection.execute(
        """
        SELECT mappings.*
        FROM evidence_mappings mappings
        JOIN profile_versions versions
          ON versions.id = mappings.profile_version_id
         AND versions.project_id = mappings.project_id
        JOIN evidence_artifacts artifacts
          ON artifacts.id = mappings.artifact_id
         AND artifacts.project_id = mappings.project_id
        JOIN evidence_versions evidence_version
          ON evidence_version.id = mappings.evidence_version_id
         AND evidence_version.artifact_id = mappings.artifact_id
         AND evidence_version.project_id = mappings.project_id
        WHERE mappings.id = ?
          AND mappings.target_type = 'profile'
          AND mappings.profile_version_id = ?
          AND mappings.project_id = ?
          AND versions.project_id = ?
        """,
        (mapping_id, version_id, project_id, project_id),
    ).fetchone()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Profile evidence mapping not found")
    return mapping


def _profile_version_or_404(connection: Any, project_id: str, version_id: str) -> Any:
    version = connection.execute(
        "SELECT * FROM profile_versions WHERE id = ? AND project_id = ?",
        (version_id, project_id),
    ).fetchone()
    if version is None:
        raise HTTPException(status_code=404, detail="Profile version not found")
    return version


def _profile_status(connection: Any, version_id: str) -> str:
    event = connection.execute(
        """
        SELECT status FROM profile_lifecycle_events
        WHERE profile_version_id = ? ORDER BY rowid DESC LIMIT 1
        """,
        (version_id,),
    ).fetchone()
    if event is None:
        raise RuntimeError(f"Profile version {version_id} has no lifecycle event")
    return cast(str, event["status"])


def _profile_content_revision(connection: Any, version_id: str) -> str:
    """Derive the review token from the complete current Profile snapshot."""
    generation = connection.execute(
        """
        SELECT COUNT(*) AS generation FROM profile_content_changes
        WHERE profile_version_id = ?
        """,
        (version_id,),
    ).fetchone()["generation"]
    return profile_snapshot_revision(connection, version_id, generation)


def _require_profile_revision(connection: Any, version_id: str, expected_revision: str) -> str:
    current_revision = _profile_content_revision(connection, version_id)
    if expected_revision != current_revision:
        raise HTTPException(
            status_code=409,
            detail="Profile snapshot changed after it was loaded; reload and review again",
        )
    return current_revision


def _profile_mapping(connection: Any, mapping: Any) -> dict[str, Any]:
    return {
        "mapping_id": mapping["mapping_id"],
        "artifact_id": mapping["artifact_id"],
        "name": mapping["name"],
        "uploaded_file_id": mapping["uploaded_file_id"],
        "evidence_version_id": mapping["evidence_version_id"],
        "version_number": mapping["version_number"],
        "sha256": mapping["sha256"],
        "relative_path": mapping["relative_path"],
        "target_type": mapping["target_type"],
        "target_key": mapping["target_key"],
        "rationale": mapping["rationale"],
        "review_state": mapping["review_state"],
        "created_at": mapping["created_at"],
    }


def _profile_version_detail(connection: Any, project_id: str, version_id: str) -> dict[str, Any]:
    version = _profile_version_or_404(connection, project_id, version_id)
    top_values = [
        {
            **_row(row),
            "target_key": f"field:{row['section']}:{row['field_key']}",
        }
        for row in connection.execute(
            """
            SELECT id, section, field_key, label, value, source, reviewer,
                   last_reviewed_at, sort_order
            FROM profile_field_values
            WHERE profile_version_id = ? AND profile_item_id IS NULL
            ORDER BY sort_order, rowid
            """,
            (version_id,),
        )
    ]
    items: list[dict[str, Any]] = []
    for item in connection.execute(
        """
        SELECT id, client_key, item_type, environment_item_id, sort_order
        FROM profile_items WHERE profile_version_id = ?
        ORDER BY sort_order, rowid
        """,
        (version_id,),
    ):
        result = _row(item)
        result["values"] = [
            {
                **_row(row),
                "target_key": f"item:{item['client_key']}:{row['field_key']}",
            }
            for row in connection.execute(
                """
                SELECT id, section, field_key, label, value, source, reviewer,
                       last_reviewed_at, sort_order
                FROM profile_field_values
                WHERE profile_version_id = ? AND profile_item_id = ?
                ORDER BY sort_order, rowid
                """,
                (version_id, item["id"]),
            )
        ]
        items.append(result)
    lifecycle = [
        {
            "id": row["id"],
            "status": row["status"],
            "actor": {"id": row["actor_id"], "display_name": row["display_name"]},
            "reviewer": row["reviewer"],
            "content_revision": row["content_revision"],
            "timestamp": row["created_at"],
        }
        for row in connection.execute(
            """
            SELECT events.*, users.display_name
            FROM profile_lifecycle_events events
            JOIN user_accounts users ON users.id = events.actor_id
            WHERE events.profile_version_id = ? ORDER BY events.rowid
            """,
            (version_id,),
        )
    ]
    evidence = [
        _profile_mapping(connection, row)
        for row in connection.execute(
            """
            SELECT mappings.id AS mapping_id, mappings.artifact_id,
                   mappings.evidence_version_id, mappings.target_type,
                   mappings.target_key, mappings.rationale, mappings.review_state,
                   mappings.created_at,
                   mappings.artifact_name_snapshot AS name,
                   mappings.uploaded_file_id_snapshot AS uploaded_file_id,
                   versions.version_number,
                   versions.sha256, versions.relative_path
            FROM evidence_mappings mappings
            JOIN evidence_versions versions ON versions.id = mappings.evidence_version_id
            WHERE mappings.target_type = 'profile'
              AND mappings.profile_version_id = ?
              AND versions.project_id = ?
            ORDER BY mappings.created_at, mappings.rowid
            """,
            (version_id, project_id),
        )
    ]
    return {
        "id": version["id"],
        "project_id": version["project_id"],
        "version_number": version["version_number"],
        "status": lifecycle[-1]["status"],
        "created_by": version["created_by"],
        "created_at": version["created_at"],
        "content_revision": _profile_content_revision(connection, version_id),
        "values": top_values,
        "items": items,
        "lifecycle": lifecycle,
        "evidence": evidence,
    }


def _profile_overview(connection: Any, project_id: str) -> dict[str, Any]:
    project = _project_or_404(connection, project_id)
    versions = [
        _profile_version_detail(connection, project_id, row["id"])
        for row in connection.execute(
            """
            SELECT id FROM profile_versions
            WHERE project_id = ? ORDER BY version_number DESC
            """,
            (project_id,),
        )
    ]
    return {
        "project_id": project_id,
        "active_version_id": project["active_profile_version_id"],
        "versions": versions,
        "template": {
            "available": False,
            "name": None,
            "message": "No framework template is released. Use the complete neutral Profile form.",
        },
    }


def _initialize_profile(connection: Any, project: dict[str, Any]) -> str:
    version_id = str(uuid4())
    connection.execute(
        """
        INSERT INTO profile_versions(
            id, project_id, version_number, created_by, created_at, content_revision
        ) VALUES (?, ?, 1, 'johnathan', ?, ?)
        """,
        (version_id, project["id"], project["created_at"], "1"),
    )
    connection.execute(
        """
        INSERT INTO profile_lifecycle_events(
            id, profile_version_id, status, actor_id, reviewer, created_at
        ) VALUES (?, ?, 'Draft', 'johnathan', '', ?)
        """,
        (str(uuid4()), version_id, project["created_at"]),
    )
    connection.execute(
        """
        INSERT INTO profile_field_values(
            id, profile_version_id, profile_item_id, section, field_key, label,
            value, source, reviewer, last_reviewed_at, sort_order
        ) VALUES (?, ?, NULL, 'project_metadata', 'project_name', 'Project name',
                  ?, 'Project creation', 'Johnathan', ?, 0)
        """,
        (str(uuid4()), version_id, project["name"], project["created_at"]),
    )
    return version_id


def _validate_profile_payload(payload: ProfileVersionSave) -> None:
    seen_keys: set[str] = set()
    target_keys: set[str] = set()
    environment_keys: set[str] = set()
    for field in payload.values:
        if ":" in field.section or ":" in field.field_key:
            raise HTTPException(
                status_code=422, detail="Profile target identity components cannot contain ':'"
            )
        target_key = _profile_target_key(None, field)
        if target_key in target_keys:
            raise HTTPException(status_code=422, detail="Profile target identities must be unique")
        target_keys.add(target_key)
        try:
            datetime.fromisoformat(field.last_reviewed_at)
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail="Profile last-reviewed timestamps must be ISO-8601"
            ) from error
    for item in payload.items:
        if item.client_key in seen_keys:
            raise HTTPException(status_code=422, detail="Profile item keys must be unique")
        seen_keys.add(item.client_key)
        if ":" in item.client_key:
            raise HTTPException(
                status_code=422, detail="Profile target identity components cannot contain ':'"
            )
        if item.item_type not in PROFILE_ITEM_TYPES:
            raise HTTPException(status_code=422, detail="Unknown Profile item type")
        fields = {field.field_key: field.value.strip() for field in item.values}
        for field in item.values:
            if ":" in field.section or ":" in field.field_key:
                raise HTTPException(
                    status_code=422,
                    detail="Profile target identity components cannot contain ':'",
                )
            target_key = _profile_target_key(item, field)
            if target_key in target_keys:
                raise HTTPException(
                    status_code=422, detail="Profile target identities must be unique"
                )
            target_keys.add(target_key)
            try:
                datetime.fromisoformat(field.last_reviewed_at)
            except ValueError as error:
                raise HTTPException(
                    status_code=422, detail="Profile last-reviewed timestamps must be ISO-8601"
                ) from error
        if item.item_type == "environment":
            environment_keys.add(item.client_key)
            if fields.get("environment_type") not in ENVIRONMENT_TYPES:
                raise HTTPException(
                    status_code=422,
                    detail="Environment type must be cloud, physical, site, or network",
                )
        if item.item_type == "unknown_follow_up":
            owner_and_date = bool(fields.get("owner") and fields.get("target_date"))
            follow_up = bool(fields.get("follow_up_reference"))
            if not (owner_and_date or follow_up):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "An unknown requires an owner and target date or an explicit "
                        "follow-up reference"
                    ),
                )
            if fields.get("target_date"):
                try:
                    date.fromisoformat(fields["target_date"])
                except ValueError as error:
                    raise HTTPException(
                        status_code=422, detail="Unknown target dates must be ISO-8601 dates"
                    ) from error
    for item in payload.items:
        if item.item_type == "scope_item" and not item.environment_item_key:
            raise HTTPException(status_code=422, detail="Scope inventory requires an environment")
        if item.item_type != "scope_item" and item.environment_item_key:
            raise HTTPException(
                status_code=422,
                detail="Only scope inventory may reference an environment",
            )
        if item.environment_item_key and item.environment_item_key not in environment_keys:
            raise HTTPException(
                status_code=422, detail="Inventory must reference an environment in this version"
            )


def _profile_payload_target_keys(payload: ProfileVersionSave) -> set[str]:
    return {
        *(_profile_target_key(None, field) for field in payload.values),
        *(_profile_target_key(item, field) for item in payload.items for field in item.values),
    }


def _project_readiness_declaration(connection: Any, project_id: str) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT framework_versions.declarations_json
        FROM projects
        JOIN framework_versions ON framework_versions.id = projects.framework_version_id
        WHERE projects.id = ?
        """,
        (project_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    declarations = cast(dict[str, Any], json.loads(row["declarations_json"]))
    return cast(dict[str, Any], declarations["profile_readiness"])


def _latest_profile_readiness_transition(connection: Any, project_id: str) -> Any:
    latest = connection.execute(
        """
        SELECT * FROM profile_readiness_transitions
        WHERE project_id = ?
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if latest is None:
        raise RuntimeError(f"Project {project_id} has no profile readiness transition")
    return latest


def _profile_readiness(connection: Any, project_id: str) -> dict[str, Any]:
    _project_or_404(connection, project_id)
    declaration = _project_readiness_declaration(connection, project_id)
    acknowledgement = connection.execute(
        """
        SELECT profile_boundary_acknowledgements.*, user_accounts.display_name
        FROM profile_boundary_acknowledgements
        JOIN user_accounts ON user_accounts.id = profile_boundary_acknowledgements.actor_id
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    latest = _latest_profile_readiness_transition(connection, project_id)
    unresolved = json.loads(latest["unresolved_required_fields_json"])
    completion = cast(dict[str, Any], declaration["profile_completion"])
    profile_blockers: list[str] = []
    if completion.get("requires_boundary_acknowledgement") and acknowledgement is None:
        profile_blockers.append(completion["boundary_acknowledgement_blocking_reason"])
    if completion.get("requires_no_unresolved_required_fields"):
        profile_blockers.extend(
            completion["unresolved_required_field_blocking_reason"].format(field=field)
            for field in unresolved
        )
    required_fields = cast(dict[str, dict[str, str]], completion["required_fields"])
    for field, requirement in required_fields.items():
        if not cast(str, latest[field]).strip():
            profile_blockers.append(requirement["blocking_reason"])
    state = cast(str, latest["next_state"])
    assessment_entry = cast(dict[str, Any], declaration["assessment_entry"])
    follow_up_rule = cast(dict[str, Any], declaration["follow_up_work"])
    assessment_exists = (
        connection.execute(
            "SELECT 1 FROM assessments WHERE project_id = ? LIMIT 1",
            (project_id,),
        ).fetchone()
        is not None
    )
    acknowledgement_result = None
    if acknowledgement is not None:
        acknowledgement_result = {
            "document_path": acknowledgement["document_path"],
            "statement": (
                "Acknowledges review of the local evidence operating boundary; "
                "this is not an attestation that content is free of CUI, PHI, or ePHI."
            ),
            "actor": {
                "id": acknowledgement["actor_id"],
                "display_name": acknowledgement["display_name"],
            },
            "timestamp": acknowledgement["created_at"],
        }
    return {
        "project_id": project_id,
        "state": state,
        "assessment_exists": assessment_exists,
        "supported_states": declaration["states"],
        "allowed_next_states": [
            candidate
            for candidate in declaration["states"]
            if candidate in declaration["transitions"][state]
        ],
        "assessment_entry_allowed": state in set(assessment_entry["allowed_states"]),
        "assessment_entry_blocking_reasons": (
            []
            if state in set(assessment_entry["allowed_states"])
            else [assessment_entry["blocking_reasons"][state]]
        ),
        "profile_completion_blocking_reasons": profile_blockers,
        "follow_up_work_required_states": follow_up_rule["required_states"],
        "follow_up_work_required_when_unresolved_required_fields": follow_up_rule[
            "required_when_unresolved_required_fields"
        ],
        "boundary_document": declaration["boundary_document"],
        "acknowledgement": acknowledgement_result,
        "current_details": {
            "unresolved_required_fields": unresolved,
            "follow_up_work": latest["follow_up_work"],
            "reviewed_by": latest["reviewed_by"],
            "approval_evidence": latest["approval_evidence"],
        },
    }


def _assessment_for_project_or_404(connection: Any, project_id: str, assessment_id: str) -> Any:
    assessment = connection.execute(
        "SELECT * FROM assessments WHERE id = ? AND project_id = ?",
        (assessment_id, project_id),
    ).fetchone()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


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


def _derived_status(connection: Any, assessment_id: str, parent_id: str) -> str:
    statuses = [
        row["status"] or ""
        for row in connection.execute(
            """
            SELECT COALESCE(determinations.status, '') AS status
            FROM framework_records
            JOIN assessments
              ON assessments.framework_version_id = framework_records.framework_version_id
            LEFT JOIN determinations
              ON determinations.assessment_id = assessments.id
             AND determinations.record_id = framework_records.record_id
            WHERE assessments.id = ? AND framework_records.parent_id = ?
            ORDER BY framework_records.sort_order
            """,
            (assessment_id, parent_id),
        )
    ]
    if not statuses:
        return ""
    rule = _framework_declarations(connection, assessment_id)["rollup_rule"]
    for status in rule["precedence"]:
        if status in statuses:
            return cast(str, status)
    blank_status = cast(str, rule.get("blank_status", ""))
    if rule.get("blank_children_prevent_met", True) and blank_status in statuses:
        return blank_status
    if all(status in set(rule["satisfied_child_statuses"]) for status in statuses):
        return cast(str, rule["satisfied_rollup_status"])
    return blank_status


def _determination(connection: Any, assessment_id: str, record: Any) -> dict[str, Any]:
    if not record["carries_determination"]:
        return {
            "status": _derived_status(connection, assessment_id, record["record_id"]),
            "derived": True,
            "na_rationale": "",
            "addressable_disposition": None,
            "disposition_reason": "",
            "interview_observation": "",
        }
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
    result["derived"] = False
    reconciliation = connection.execute(
        "SELECT id, outcome, finding_id, corrective_action_id, rationale, updated_at "
        "FROM not_met_reconciliations WHERE assessment_id = ? AND record_id = ?",
        (assessment_id, record["record_id"]),
    ).fetchone()
    result["reconciliation"] = _row(reconciliation) if reconciliation else None
    return result


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
        "editable_determination": bool(record["carries_determination"]),
    }
    result["determination"] = _determination(connection, assessment_id, record)
    return result


def _prompts_for_record(
    connection: Any,
    assessment_id: str,
    framework_version_id: str,
    record_id: str | None,
) -> list[dict[str, Any]]:
    prompt_rows = connection.execute(
        """
        SELECT fp.*, pa.answer
        FROM framework_prompts fp
        LEFT JOIN prompt_answers pa
          ON pa.prompt_id = fp.prompt_id AND pa.assessment_id = ?
        WHERE fp.framework_version_id = ?
          AND fp.original_record_id = ?
        ORDER BY fp.sort_order
        """,
        (
            assessment_id,
            framework_version_id,
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
        }
        prompts.append(item)
    return prompts


def _walkthrough_records(connection: Any, framework_version_id: str) -> list[Any]:
    framework = connection.execute(
        "SELECT declarations_json FROM framework_versions WHERE id = ?",
        (framework_version_id,),
    ).fetchone()
    membership = json.loads(framework["declarations_json"])["walkthrough_membership"]
    if membership != "all_records":
        raise ValueError(f"Unsupported walkthrough membership rule: {membership}")
    records: list[Any] = connection.execute(
        """
        SELECT * FROM framework_records
        WHERE framework_version_id = ?
        ORDER BY sort_order
        """,
        (framework_version_id,),
    ).fetchall()
    return records


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
            "shared_record_count": connection.execute(
                "SELECT COUNT(*) AS count FROM evidence_mappings "
                "WHERE artifact_id = ? AND target_type = 'assessment_record'",
                (mapping["artifact_id"],),
            ).fetchone()["count"],
        }
        for mapping in connection.execute(
            """
            SELECT em.id AS mapping_id, em.artifact_id, ea.name, ea.relative_path,
                   em.rationale, em.review_state, ev.id AS version_id,
                   ev.version_number, ev.sha256
            FROM evidence_mappings em
            JOIN evidence_artifacts ea ON ea.id = em.artifact_id
            JOIN evidence_versions ev ON ev.id = em.evidence_version_id
            WHERE em.target_type = 'assessment_record'
              AND em.assessment_id = ? AND em.record_id = ?
            ORDER BY em.created_at
            """,
            (assessment_id, record_id),
        )
    ]
    work_ids = [
        row["record_id"]
        for row in _walkthrough_records(connection, assessment["framework_version_id"])
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
        "no_prompt_explanation": record["no_prompt_explanation"],
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
    managed_storage = storage_path or root / "data" / "files"
    database = Database(database_path or root / "data" / "workspace.db", managed_storage)
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

    @app.exception_handler(sqlite3.IntegrityError)
    async def profile_integrity_error(
        _request: Request, _error: sqlite3.IntegrityError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "The requested mutation violates a persisted integrity rule."},
        )

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

    @app.get("/api/projects/{project_id}/close-readiness/{target}")
    def get_close_readiness(project_id: str, target: str, database: Annotated[Database, Depends(db)]) -> dict[str, Any]:
        if target != "fieldwork_ready_for_generation":
            raise HTTPException(422, "Unknown close-readiness target")
        with database.connect() as connection:
            return fieldwork_ready(connection, project_id)

    @app.get("/api/projects/{project_id}/assessments/{assessment_id}/close-readiness")
    def get_assessment_close_readiness(project_id: str, assessment_id: str, database: Annotated[Database, Depends(db)], target: str = "fieldwork_ready_for_generation") -> dict[str, Any]:
        if target != "fieldwork_ready_for_generation":
            raise HTTPException(422, "Unknown close-readiness target")
        with database.connect() as connection:
            return fieldwork_ready(connection, project_id, assessment_id)

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
            declaration = _project_readiness_declaration(connection, item["id"])
            initial_state = cast(str, declaration["initial_state"])
            connection.execute(
                """
                INSERT INTO profile_readiness_transitions(
                    id, project_id, prior_state, next_state, actor_id, decision_note,
                    unresolved_required_fields_json, follow_up_work, reviewed_by,
                    approval_evidence, created_at
                ) VALUES (?, ?, ?, ?, 'johnathan',
                          'Profile readiness initialized.', '[]', '', '', '', ?)
                """,
                (str(uuid4()), item["id"], initial_state, initial_state, item["created_at"]),
            )
            _initialize_profile(connection, item)
            _audit(connection, "project.created", "project", item["id"], {"name": item["name"]})
        return item

    @app.get("/api/projects/{project_id}/profile")
    def get_profile(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            return _profile_overview(connection, project_id)

    @app.get("/api/projects/{project_id}/profile/versions/{version_id}")
    def get_profile_version(
        project_id: str,
        version_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            return _profile_version_detail(connection, project_id, version_id)

    @app.post("/api/projects/{project_id}/profile/versions", status_code=201)
    def create_profile_version(
        project_id: str,
        payload: ProfileVersionCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            _user_or_422(connection, payload.actor_id)
            base = None
            if payload.base_version_id:
                base = _profile_version_or_404(connection, project_id, payload.base_version_id)
            next_number = connection.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS number "
                "FROM profile_versions WHERE project_id = ?",
                (project_id,),
            ).fetchone()["number"]
            version_id = str(uuid4())
            created_at = now()
            connection.execute(
                """
                INSERT INTO profile_versions(
                    id, project_id, version_number, created_by, created_at, content_revision
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    project_id,
                    next_number,
                    payload.actor_id,
                    created_at,
                    "1",
                ),
            )
            connection.execute(
                """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer, created_at
                ) VALUES (?, ?, 'Draft', ?, '', ?)
                """,
                (str(uuid4()), version_id, payload.actor_id, created_at),
            )
            if base is not None:
                item_ids: dict[str, str] = {}
                base_items = connection.execute(
                    """
                    SELECT * FROM profile_items
                    WHERE profile_version_id = ? ORDER BY sort_order, rowid
                    """,
                    (base["id"],),
                ).fetchall()
                for item in sorted(
                    base_items,
                    key=lambda row: (
                        row["item_type"] != "environment",
                        row["sort_order"],
                    ),
                ):
                    item_ids[item["id"]] = str(uuid4())
                for item in sorted(
                    base_items,
                    key=lambda row: (
                        row["item_type"] != "environment",
                        row["sort_order"],
                    ),
                ):
                    connection.execute(
                        """
                        INSERT INTO profile_items(
                            id, profile_version_id, client_key, item_type,
                            environment_item_id, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item_ids[item["id"]],
                            version_id,
                            item["client_key"],
                            item["item_type"],
                            item_ids.get(item["environment_item_id"]),
                            item["sort_order"],
                        ),
                    )
                for field in connection.execute(
                    """
                    SELECT * FROM profile_field_values
                    WHERE profile_version_id = ? ORDER BY sort_order, rowid
                    """,
                    (base["id"],),
                ):
                    connection.execute(
                        """
                        INSERT INTO profile_field_values(
                            id, profile_version_id, profile_item_id, section, field_key,
                            label, value, source, reviewer, last_reviewed_at, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            version_id,
                            item_ids.get(field["profile_item_id"]),
                            field["section"],
                            field["field_key"],
                            field["label"],
                            field["value"],
                            field["source"],
                            field["reviewer"],
                            field["last_reviewed_at"],
                            field["sort_order"],
                        ),
                    )
                for mapping in connection.execute(
                    """
                    SELECT * FROM evidence_mappings
                    WHERE target_type = 'profile' AND profile_version_id = ?
                    ORDER BY created_at, rowid
                    """,
                    (base["id"],),
                ):
                    connection.execute(
                        """
                        INSERT INTO evidence_mappings(
                            id, project_id, artifact_id, evidence_version_id, target_type,
                            assessment_id, record_id, profile_version_id, target_key,
                            artifact_name_snapshot, uploaded_file_id_snapshot,
                            rationale, review_state, created_at
                        ) VALUES (
                            ?, ?, ?, ?, 'profile', NULL, NULL, ?, ?, ?, ?,
                            ?, 'Not reviewed', ?
                        )
                        """,
                        (
                            str(uuid4()),
                            project_id,
                            mapping["artifact_id"],
                            mapping["evidence_version_id"],
                            version_id,
                            mapping["target_key"],
                            mapping["artifact_name_snapshot"],
                            mapping["uploaded_file_id_snapshot"],
                            mapping["rationale"],
                            created_at,
                        ),
                    )
            _profile_content_revision(connection, version_id)
            _audit(
                connection,
                "profile.version_created",
                "profile_version",
                version_id,
                {
                    "project_id": project_id,
                    "version_number": next_number,
                    "base_version_id": payload.base_version_id,
                },
                payload.actor_id,
            )
            return _profile_version_detail(connection, project_id, version_id)

    @app.put("/api/projects/{project_id}/profile/versions/{version_id}")
    def save_profile_version(
        project_id: str,
        version_id: str,
        payload: ProfileVersionSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        _validate_profile_payload(payload)
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _user_or_422(connection, payload.actor_id)
            _profile_version_or_404(connection, project_id, version_id)
            _require_profile_revision(connection, version_id, payload.expected_revision)
            if _profile_status(connection, version_id) != "Draft":
                raise HTTPException(
                    status_code=409,
                    detail="Reviewed and approved Profile versions are immutable",
                )
            retained_targets = _profile_payload_target_keys(payload)
            existing_targets = {
                row["target_key"]
                for row in connection.execute(
                    """
                    SELECT target_key FROM evidence_mappings
                    WHERE target_type = 'profile' AND profile_version_id = ?
                    """,
                    (version_id,),
                )
            }
            if not existing_targets <= retained_targets:
                raise HTTPException(
                    status_code=409,
                    detail="Draft cannot remove a Profile field that has mapped evidence",
                )
            preserved_mappings = connection.execute(
                """
                SELECT * FROM evidence_mappings
                WHERE target_type = 'profile' AND profile_version_id = ?
                ORDER BY created_at, rowid
                """,
                (version_id,),
            ).fetchall()
            connection.execute(
                """
                DELETE FROM evidence_mappings
                WHERE target_type = 'profile' AND profile_version_id = ?
                """,
                (version_id,),
            )
            connection.execute(
                "DELETE FROM profile_field_values WHERE profile_version_id = ?",
                (version_id,),
            )
            connection.execute(
                "DELETE FROM profile_items WHERE profile_version_id = ?",
                (version_id,),
            )
            for order, field in enumerate(payload.values):
                connection.execute(
                    """
                    INSERT INTO profile_field_values(
                        id, profile_version_id, profile_item_id, section, field_key,
                        label, value, source, reviewer, last_reviewed_at, sort_order
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        version_id,
                        field.section,
                        field.field_key,
                        field.label,
                        field.value,
                        field.source,
                        field.reviewer,
                        field.last_reviewed_at,
                        order,
                    ),
                )
            item_ids = {item.client_key: str(uuid4()) for item in payload.items}
            item_orders = {item.client_key: order for order, item in enumerate(payload.items)}
            for item in sorted(
                payload.items,
                key=lambda candidate: (
                    candidate.item_type != "environment",
                    item_orders[candidate.client_key],
                ),
            ):
                connection.execute(
                    """
                    INSERT INTO profile_items(
                        id, profile_version_id, client_key, item_type,
                        environment_item_id, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_ids[item.client_key],
                        version_id,
                        item.client_key,
                        item.item_type,
                        (
                            item_ids[item.environment_item_key]
                            if item.environment_item_key
                            else None
                        ),
                        item_orders[item.client_key],
                    ),
                )
            field_order = len(payload.values)
            for item in payload.items:
                for field in item.values:
                    connection.execute(
                        """
                        INSERT INTO profile_field_values(
                            id, profile_version_id, profile_item_id, section, field_key,
                            label, value, source, reviewer, last_reviewed_at, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            version_id,
                            item_ids[item.client_key],
                            field.section,
                            field.field_key,
                            field.label,
                            field.value,
                            field.source,
                            field.reviewer,
                            field.last_reviewed_at,
                            field_order,
                        ),
                    )
                    field_order += 1
            for mapping in preserved_mappings:
                connection.execute(
                    """
                    INSERT INTO evidence_mappings(
                        id, project_id, artifact_id, evidence_version_id, target_type,
                        assessment_id, record_id, profile_version_id, target_key,
                        artifact_name_snapshot, uploaded_file_id_snapshot,
                        rationale, review_state, created_at
                    ) VALUES (?, ?, ?, ?, 'profile', NULL, NULL, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mapping["id"],
                        project_id,
                        mapping["artifact_id"],
                        mapping["evidence_version_id"],
                        version_id,
                        mapping["target_key"],
                        mapping["artifact_name_snapshot"],
                        mapping["uploaded_file_id_snapshot"],
                        mapping["rationale"],
                        mapping["review_state"],
                        mapping["created_at"],
                    ),
                )
            _profile_content_revision(connection, version_id)
            _audit(
                connection,
                "profile.version_saved",
                "profile_version",
                version_id,
                {"project_id": project_id},
                payload.actor_id,
            )
            return _profile_version_detail(connection, project_id, version_id)

    @app.post(
        "/api/projects/{project_id}/profile/versions/{version_id}/lifecycle",
        status_code=201,
    )
    def create_profile_lifecycle_event(
        project_id: str,
        version_id: str,
        payload: ProfileLifecycleCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _user_or_422(connection, payload.actor_id)
            _profile_version_or_404(connection, project_id, version_id)
            reviewed_revision = _require_profile_revision(
                connection, version_id, payload.expected_revision
            )
            current = _profile_status(connection, version_id)
            expected = {"Draft": "Reviewed", "Reviewed": "Approved"}.get(current)
            if payload.status != expected:
                raise HTTPException(
                    status_code=422,
                    detail="Profile lifecycle must follow Draft to Reviewed to Approved",
                )
            reviewer = payload.reviewer.strip()
            if payload.status == "Approved" and not reviewer:
                raise HTTPException(status_code=422, detail="Approval requires a named reviewer")
            event_id = str(uuid4())
            created_at = now()
            connection.execute(
                """
                INSERT INTO profile_lifecycle_events(
                    id, profile_version_id, status, actor_id, reviewer,
                    content_revision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    version_id,
                    payload.status,
                    payload.actor_id,
                    reviewer,
                    reviewed_revision,
                    created_at,
                ),
            )
            _audit(
                connection,
                "profile.lifecycle_recorded",
                "profile_lifecycle_event",
                event_id,
                {
                    "project_id": project_id,
                    "profile_version_id": version_id,
                    "status": payload.status,
                    "reviewer": reviewer,
                    "content_revision": reviewed_revision,
                },
                payload.actor_id,
            )
            if payload.status == "Approved":
                _audit(
                    connection,
                    "profile.version_approved",
                    "profile_version",
                    version_id,
                    {
                        "project_id": project_id,
                        "reviewer": reviewer,
                        "content_revision": reviewed_revision,
                    },
                    payload.actor_id,
                )
            overview = _profile_overview(connection, project_id)
            return {
                "active_version_id": overview["active_version_id"],
                "version": _profile_version_detail(connection, project_id, version_id),
            }

    @app.post(
        "/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings",
        status_code=201,
    )
    def create_profile_evidence_mapping(
        project_id: str,
        version_id: str,
        payload: ProfileEvidenceMappingCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _user_or_422(connection, payload.actor_id)
            _profile_version_or_404(connection, project_id, version_id)
            _require_profile_revision(connection, version_id, payload.expected_revision)
            if _profile_status(connection, version_id) != "Draft":
                raise HTTPException(
                    status_code=409, detail="Approved Profile snapshots are immutable"
                )
            _profile_target_or_404(connection, project_id, version_id, payload.target_key)
            artifact = connection.execute(
                """
                SELECT artifacts.id
                FROM evidence_artifacts artifacts
                JOIN evidence_versions versions ON versions.artifact_id = artifacts.id
                WHERE artifacts.id = ? AND artifacts.project_id = ?
                  AND versions.id = ? AND versions.project_id = ?
                """,
                (
                    payload.artifact_id,
                    project_id,
                    payload.evidence_version_id,
                    project_id,
                ),
            ).fetchone()
            if artifact is None:
                raise HTTPException(status_code=404, detail="Evidence artifact/version not found")
            mapping_id = str(uuid4())
            created_at = now()
            try:
                connection.execute(
                    """
                INSERT INTO evidence_mappings(
                    id, project_id, artifact_id, evidence_version_id, target_type,
                    assessment_id, record_id, profile_version_id, target_key,
                    artifact_name_snapshot, uploaded_file_id_snapshot,
                    rationale, review_state, created_at
                )
                SELECT ?, ?, ?, ?, 'profile', NULL, NULL, ?, ?, name, uploaded_file_id,
                       ?, 'Not reviewed', ?
                FROM evidence_artifacts WHERE id = ? AND project_id = ?
                    """,
                    (
                        mapping_id,
                        project_id,
                        payload.artifact_id,
                        payload.evidence_version_id,
                        version_id,
                        payload.target_key.strip(),
                        payload.rationale.strip(),
                        created_at,
                        payload.artifact_id,
                        project_id,
                    ),
                )
            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    raise HTTPException(
                        status_code=409,
                        detail="Evidence version is already mapped to this Profile target",
                    ) from error
                raise
            _audit(
                connection,
                "evidence.mapped",
                "evidence_mapping",
                mapping_id,
                {
                    "project_id": project_id,
                    "profile_version_id": version_id,
                    "target_type": "profile",
                    "target_key": payload.target_key.strip(),
                    "artifact_id": payload.artifact_id,
                },
                payload.actor_id,
            )
            row = connection.execute(
                """
                SELECT mappings.id AS mapping_id, mappings.artifact_id,
                       mappings.evidence_version_id, mappings.target_type,
                       mappings.target_key, mappings.rationale, mappings.review_state,
                       mappings.created_at,
                       mappings.artifact_name_snapshot AS name,
                       mappings.uploaded_file_id_snapshot AS uploaded_file_id,
                       versions.version_number,
                       versions.sha256, versions.relative_path
                FROM evidence_mappings mappings
                JOIN evidence_versions versions ON versions.id = mappings.evidence_version_id
                WHERE mappings.id = ?
                """,
                (mapping_id,),
            ).fetchone()
            result = _profile_mapping(connection, row)
            result["content_revision"] = _profile_content_revision(connection, version_id)
            return result

    @app.post(
        "/api/projects/{project_id}/profile/versions/{version_id}/evidence",
        status_code=201,
    )
    async def create_profile_evidence(
        project_id: str,
        version_id: str,
        target_key: Annotated[str, Form(min_length=1, max_length=300)],
        rationale: Annotated[str, Form(min_length=1, max_length=2000)],
        expected_revision: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
        database: Annotated[Database, Depends(db)],
        file_storage: Annotated[FileStorage, Depends(files)],
        actor_id: Annotated[str, Form()] = "johnathan",
    ) -> dict[str, Any]:
        if not file.filename:
            raise HTTPException(status_code=422, detail="Evidence filename is required")
        content = await file.read()
        artifact_id = str(uuid4())
        uploaded_file_id = str(uuid4())
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _user_or_422(connection, actor_id)
            _profile_version_or_404(connection, project_id, version_id)
            _require_profile_revision(connection, version_id, expected_revision)
            if _profile_status(connection, version_id) != "Draft":
                raise HTTPException(
                    status_code=409, detail="Approved Profile snapshots are immutable"
                )
            _profile_target_or_404(connection, project_id, version_id, target_key)
            staged_path, relative_path = file_storage.stage(
                project_id, artifact_id, file.filename, content
            )
            created_at = now()
            version = {
                "id": str(uuid4()),
                "project_id": project_id,
                "version_number": 1,
                "sha256": sha256(file_storage.read(staged_path)).hexdigest(),
                "relative_path": relative_path,
                "created_at": created_at,
            }
            try:
                connection.execute(
                    """
                    INSERT INTO evidence_artifacts(
                        id, project_id, name, relative_path, created_at, uploaded_file_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        project_id,
                        file.filename,
                        relative_path,
                        created_at,
                        uploaded_file_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO evidence_versions(
                        id, artifact_id, project_id, version_number,
                        relative_path, sha256, created_at
                    ) VALUES (?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        version["id"],
                        artifact_id,
                        project_id,
                        relative_path,
                        version["sha256"],
                        created_at,
                    ),
                )
                mapping_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO evidence_mappings(
                        id, project_id, artifact_id, evidence_version_id, target_type,
                        assessment_id, record_id, profile_version_id, target_key,
                        artifact_name_snapshot, uploaded_file_id_snapshot,
                        rationale, review_state, created_at
                    ) VALUES (
                        ?, ?, ?, ?, 'profile', NULL, NULL, ?, ?, ?, ?,
                        ?, 'Not reviewed', ?
                    )
                    """,
                    (
                        mapping_id,
                        project_id,
                        artifact_id,
                        version["id"],
                        version_id,
                        target_key.strip(),
                        file.filename,
                        uploaded_file_id,
                        rationale.strip(),
                        created_at,
                    ),
                )
            except Exception:
                file_storage.delete(staged_path)
                raise
            try:
                _audit(
                    connection,
                    "evidence.created",
                    "evidence_artifact",
                    artifact_id,
                    {
                        "project_id": project_id,
                        "name": file.filename,
                        "uploaded_file_id": uploaded_file_id,
                        "profile_version_id": version_id,
                    },
                    actor_id,
                )
                _audit(
                    connection,
                    "evidence.mapped",
                    "evidence_mapping",
                    mapping_id,
                    {
                        "project_id": project_id,
                        "profile_version_id": version_id,
                        "target_type": "profile",
                        "target_key": target_key.strip(),
                        "artifact_id": artifact_id,
                    },
                    actor_id,
                )
                mapping = connection.execute(
                    """
                    SELECT mappings.id AS mapping_id, mappings.artifact_id,
                           mappings.evidence_version_id, mappings.target_type,
                           mappings.target_key, mappings.rationale, mappings.review_state,
                           mappings.created_at,
                           mappings.artifact_name_snapshot AS name,
                           mappings.uploaded_file_id_snapshot AS uploaded_file_id,
                           versions.version_number, versions.sha256, versions.relative_path
                    FROM evidence_mappings mappings
                    JOIN evidence_versions versions ON versions.id = mappings.evidence_version_id
                    WHERE mappings.id = ?
                    """,
                    (mapping_id,),
                ).fetchone()
                file_storage.promote(staged_path, relative_path)
            except Exception:
                file_storage.delete(staged_path)
                file_storage.delete(relative_path)
                raise
            return {
                "artifact": {
                    "id": artifact_id,
                    "project_id": project_id,
                    "name": file.filename,
                    "uploaded_file_id": uploaded_file_id,
                    "relative_path": relative_path,
                    "created_at": created_at,
                    "version": version,
                },
                "mapping": _profile_mapping(connection, mapping),
                "content_revision": _profile_content_revision(connection, version_id),
            }

    @app.put(
        "/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings/{mapping_id}"
    )
    def update_profile_evidence_mapping(
        project_id: str,
        version_id: str,
        mapping_id: str,
        payload: ProfileEvidenceMappingUpdate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _user_or_422(connection, payload.actor_id)
            _profile_version_or_404(connection, project_id, version_id)
            _require_profile_revision(connection, version_id, payload.expected_revision)
            mapping = _profile_mapping_destination_or_404(
                connection, project_id, version_id, mapping_id
            )
            if _profile_status(connection, version_id) != "Draft":
                raise HTTPException(
                    status_code=409, detail="Reviewed and approved Profile snapshots are immutable"
                )
            _profile_target_or_404(connection, project_id, version_id, payload.target_key)
            connection.execute(
                """
                UPDATE evidence_mappings
                SET target_key = ?, rationale = ?
                WHERE id = ? AND project_id = ? AND target_type = 'profile'
                  AND profile_version_id = ?
                """,
                (
                    payload.target_key.strip(),
                    payload.rationale.strip(),
                    mapping_id,
                    project_id,
                    version_id,
                ),
            )
            _audit(
                connection,
                "evidence.mapping_updated",
                "evidence_mapping",
                mapping_id,
                {
                    "project_id": project_id,
                    "profile_version_id": version_id,
                    "artifact_id": mapping["artifact_id"],
                    "target_key": payload.target_key.strip(),
                },
                payload.actor_id,
            )
            row = connection.execute(
                """
                SELECT mappings.id AS mapping_id, mappings.artifact_id,
                       mappings.evidence_version_id, mappings.target_type,
                       mappings.target_key, mappings.rationale, mappings.review_state,
                       mappings.created_at,
                       mappings.artifact_name_snapshot AS name,
                       mappings.uploaded_file_id_snapshot AS uploaded_file_id,
                       versions.version_number, versions.sha256, versions.relative_path
                FROM evidence_mappings mappings
                JOIN evidence_versions versions ON versions.id = mappings.evidence_version_id
                WHERE mappings.id = ?
                """,
                (mapping_id,),
            ).fetchone()
            result = _profile_mapping(connection, row)
            result["content_revision"] = _profile_content_revision(connection, version_id)
            return result

    @app.delete(
        "/api/projects/{project_id}/profile/versions/{version_id}/evidence-mappings/{mapping_id}"
    )
    def delete_profile_evidence_mapping(
        project_id: str,
        version_id: str,
        mapping_id: str,
        database: Annotated[Database, Depends(db)],
        expected_revision: str,
        actor_id: str = "johnathan",
    ) -> dict[str, Any]:
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _user_or_422(connection, actor_id)
            _profile_version_or_404(connection, project_id, version_id)
            _require_profile_revision(connection, version_id, expected_revision)
            mapping = _profile_mapping_destination_or_404(
                connection, project_id, version_id, mapping_id
            )
            if _profile_status(connection, version_id) != "Draft":
                raise HTTPException(
                    status_code=409, detail="Reviewed and approved Profile snapshots are immutable"
                )
            deleted = connection.execute(
                """
                DELETE FROM evidence_mappings
                WHERE id = ? AND project_id = ? AND target_type = 'profile'
                  AND profile_version_id = ?
                """,
                (mapping_id, project_id, version_id),
            )
            if deleted.rowcount != 1:
                raise HTTPException(status_code=404, detail="Profile evidence mapping not found")
            _audit(
                connection,
                "evidence.unmapped",
                "evidence_mapping",
                mapping_id,
                {
                    "project_id": project_id,
                    "profile_version_id": version_id,
                    "artifact_id": mapping["artifact_id"],
                },
                actor_id,
            )
            return {
                "deleted": True,
                "content_revision": _profile_content_revision(connection, version_id),
            }

    @app.get("/api/projects/{project_id}/profile/audit")
    def list_profile_audit(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            rows = connection.execute(
                """
                SELECT events.*, users.display_name
                FROM audit_events events
                JOIN user_accounts users ON users.id = events.actor_id
                WHERE json_extract(events.details_json, '$.project_id') = ?
                  AND (
                    events.action LIKE 'profile.%'
                    OR (
                        events.action IN ('evidence.created', 'evidence.mapped')
                        AND json_extract(events.details_json, '$.profile_version_id') IS NOT NULL
                    )
                  )
                ORDER BY events.created_at, events.rowid
                """,
                (project_id,),
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

    @app.get("/api/projects/{project_id}/profile-readiness")
    def get_profile_readiness(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            return _profile_readiness(connection, project_id)

    @app.post("/api/projects/{project_id}/profile-readiness/acknowledgement", status_code=201)
    def acknowledge_profile_boundary(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            declaration = _project_readiness_declaration(connection, project_id)
            acknowledgement_id = str(uuid4())
            created_at = now()
            result = connection.execute(
                """
                INSERT OR IGNORE INTO profile_boundary_acknowledgements(
                    id, project_id, document_path, actor_id, created_at
                ) VALUES (?, ?, ?, 'johnathan', ?)
                """,
                (acknowledgement_id, project_id, declaration["boundary_document"], created_at),
            )
            if result.rowcount:
                _audit(
                    connection,
                    "profile.boundary_acknowledged",
                    "project",
                    project_id,
                    {"document_path": declaration["boundary_document"]},
                )
            acknowledgement = _profile_readiness(connection, project_id)["acknowledgement"]
            return cast(dict[str, Any], acknowledgement)

    @app.get("/api/projects/{project_id}/profile-readiness/transitions")
    def list_profile_readiness_transitions(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            return [
                {
                    "id": row["id"],
                    "prior_state": row["prior_state"],
                    "next_state": row["next_state"],
                    "actor": {
                        "id": row["actor_id"],
                        "display_name": row["display_name"],
                    },
                    "timestamp": row["created_at"],
                    "decision_note": row["decision_note"],
                    "unresolved_required_fields": json.loads(
                        row["unresolved_required_fields_json"]
                    ),
                    "follow_up_work": row["follow_up_work"],
                    "reviewed_by": row["reviewed_by"],
                    "approval_evidence": row["approval_evidence"],
                }
                for row in connection.execute(
                    """
                    SELECT profile_readiness_transitions.*, user_accounts.display_name
                    FROM profile_readiness_transitions
                    JOIN user_accounts
                      ON user_accounts.id = profile_readiness_transitions.actor_id
                    WHERE project_id = ?
                    ORDER BY profile_readiness_transitions.rowid
                    """,
                    (project_id,),
                )
            ]

    @app.post(
        "/api/projects/{project_id}/profile-readiness/transitions",
        status_code=201,
    )
    def create_profile_readiness_transition(
        project_id: str,
        payload: ProfileReadinessTransitionCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            declaration = _project_readiness_declaration(connection, project_id)
            prior_state = cast(
                str,
                _latest_profile_readiness_transition(connection, project_id)["next_state"],
            )
            next_state = payload.next_state
            if next_state not in set(declaration["states"]):
                raise HTTPException(status_code=422, detail="Unknown profile readiness state")
            transitions = cast(dict[str, list[str]], declaration["transitions"])
            if next_state not in transitions[prior_state]:
                raise HTTPException(
                    status_code=422,
                    detail=f"Cannot transition from {prior_state} to {next_state}",
                )
            if (
                declaration.get("requires_boundary_acknowledgement_before_transition")
                and connection.execute(
                    "SELECT id FROM profile_boundary_acknowledgements WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                is None
            ):
                raise HTTPException(
                    status_code=422,
                    detail=declaration["boundary_acknowledgement_validation_message"],
                )
            unresolved = [
                value.strip() for value in payload.unresolved_required_fields if value.strip()
            ]
            if not payload.decision_note.strip():
                raise HTTPException(status_code=422, detail="Decision note is required")
            completion = cast(dict[str, Any], declaration["profile_completion"])
            follow_up_rule = cast(dict[str, Any], declaration["follow_up_work"])
            follow_up_work = payload.follow_up_work.strip()
            if next_state == completion["state"]:
                if completion.get("requires_no_unresolved_required_fields") and unresolved:
                    raise HTTPException(
                        status_code=422,
                        detail=completion["unresolved_required_fields_validation_message"],
                    )
                required_fields = cast(
                    dict[str, dict[str, str]],
                    completion["required_fields"],
                )
                for field, requirement in required_fields.items():
                    if not cast(str, getattr(payload, field)).strip():
                        raise HTTPException(
                            status_code=422,
                            detail=requirement["validation_message"],
                        )
            if next_state in set(follow_up_rule["required_states"]) and not follow_up_work:
                raise HTTPException(
                    status_code=422,
                    detail=follow_up_rule["required_state_validation_messages"][next_state],
                )
            if (
                unresolved
                and follow_up_rule["required_when_unresolved_required_fields"]
                and not follow_up_work
            ):
                raise HTTPException(
                    status_code=422,
                    detail=follow_up_rule["unresolved_required_fields_validation_message"],
                )
            transition_id = str(uuid4())
            created_at = now()
            connection.execute(
                """
                INSERT INTO profile_readiness_transitions(
                    id, project_id, prior_state, next_state, actor_id, decision_note,
                    unresolved_required_fields_json, follow_up_work, reviewed_by,
                    approval_evidence, created_at
                ) VALUES (?, ?, ?, ?, 'johnathan', ?, ?, ?, ?, ?, ?)
                """,
                (
                    transition_id,
                    project_id,
                    prior_state,
                    next_state,
                    payload.decision_note.strip(),
                    json.dumps(unresolved),
                    follow_up_work,
                    payload.reviewed_by.strip(),
                    payload.approval_evidence.strip(),
                    created_at,
                ),
            )
            _audit(
                connection,
                "profile.readiness_transitioned",
                "project",
                project_id,
                {
                    "transition_id": transition_id,
                    "prior_state": prior_state,
                    "next_state": next_state,
                    "decision_note": payload.decision_note.strip(),
                },
            )
            return _profile_readiness(connection, project_id)

    @app.post("/api/projects/{project_id}/assessments", status_code=201)
    def create_assessment(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            project = _project_or_404(connection, project_id)
            readiness = _profile_readiness(connection, project_id)
            if not readiness["assessment_entry_allowed"]:
                raise HTTPException(
                    status_code=409,
                    detail=readiness["assessment_entry_blocking_reasons"],
                )
            existing = connection.execute(
                "SELECT id FROM assessments WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if existing is not None:
                raise HTTPException(status_code=409, detail="Project already has an assessment")
            assessment = {
                "id": str(uuid4()),
                "project_id": project_id,
                "framework_version_id": project["framework_version_id"],
                "created_at": now(),
            }
            connection.execute(
                """
                INSERT INTO assessments(id, project_id, framework_version_id, created_at)
                VALUES (:id, :project_id, :framework_version_id, :created_at)
                """,
                assessment,
            )
            _audit(
                connection,
                "assessment.created",
                "assessment",
                assessment["id"],
                {
                    "project_id": project_id,
                    "framework_version_id": assessment["framework_version_id"],
                },
            )
            return assessment

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
            walkthrough_rows = _walkthrough_records(connection, assessment["framework_version_id"])
            work_list = [
                {
                    **_row(row),
                    "editable_determination": bool(row["carries_determination"]),
                }
                for row in walkthrough_rows
            ]
            determination_record_count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM framework_records
                WHERE framework_version_id = ? AND carries_determination = 1
                """,
                (assessment["framework_version_id"],),
            ).fetchone()["count"]
            resolved_determination_count = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM determinations
                JOIN framework_records
                  ON framework_records.framework_version_id = ?
                 AND framework_records.record_id = determinations.record_id
                WHERE determinations.assessment_id = ?
                  AND framework_records.carries_determination = 1
                  AND determinations.status IN ('Met', 'Not Met', 'N/A')
                """,
                (assessment["framework_version_id"], assessment["id"]),
            ).fetchone()["count"]
            record_index = [
                {
                    **_row(row),
                    "editable_determination": bool(row["carries_determination"]),
                }
                for row in connection.execute(
                    """
                    SELECT record_id, citation, title, work_area, record_type, parent_id,
                           designation, sort_order, carries_determination
                    FROM framework_records
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
                    "walkthrough_record_count": len(work_list),
                    "prompt_count": framework["prompt_count"],
                    "determination_record_count": determination_record_count,
                    "declarations": json.loads(framework["declarations_json"]),
                },
                "progress": {
                    "resolved_determination_count": resolved_determination_count,
                    "determination_record_count": determination_record_count,
                },
                "work_list": work_list,
                "record_index": record_index,
            }

    @app.get("/api/projects/{project_id}/assessments/{assessment_id}/records/{record_id}")
    def get_record(
        project_id: str,
        assessment_id: str,
        record_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
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
            if payload.status == "N/A" and not payload.na_rationale.strip():
                raise HTTPException(status_code=422, detail="N/A requires a rationale")
            designation_rule = declarations.get("designation_rules", {}).get(record["designation"])
            if designation_rule:
                if payload.addressable_disposition not in set(designation_rule["dispositions"]):
                    raise HTTPException(
                        status_code=422,
                        detail="Addressable specifications require a disposition",
                    )
                if (
                    payload.addressable_disposition in set(designation_rule["reason_required_for"])
                    and not payload.disposition_reason.strip()
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="This addressable disposition requires reasoning",
                    )
            if payload.status == "Met":
                blocked = connection.execute(
                    """SELECT 1 FROM not_met_reconciliations r JOIN corrective_actions a
                       ON a.id = r.corrective_action_id AND a.project_id = r.project_id
                       WHERE r.assessment_id = ? AND r.record_id = ?
                         AND a.validation_state != 'Validated'""",
                    (assessment_id, record_id),
                ).fetchone()
                if blocked is not None:
                    raise HTTPException(
                        422, "Linked corrective action must be validated before Met"
                    )
            if payload.status == "Met" and not payload.interview_observation.strip():
                evidence = connection.execute(
                    """
                    SELECT id FROM evidence_mappings
                    WHERE target_type = 'assessment_record'
                      AND assessment_id = ? AND record_id = ? LIMIT 1
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

    @app.get(
        "/api/projects/{project_id}/assessments/{assessment_id}/records/{record_id}/reconciliation"
    )
    def get_reconciliation(
        project_id: str,
        assessment_id: str,
        record_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
            record = _record_or_404(connection, assessment_id, record_id)
            row = connection.execute(
                """
                SELECT * FROM not_met_reconciliations
                WHERE project_id = ? AND assessment_id = ? AND record_id = ?
                """,
                (project_id, assessment_id, record_id),
            ).fetchone()
            links: list[dict[str, Any]] = []
            if row and row["finding_id"]:
                finding = connection.execute(
                    "SELECT * FROM findings WHERE id = ? AND project_id = ?",
                    (row["finding_id"], project_id),
                ).fetchone()
                if finding:
                    links.append({"type": "finding", **_row(finding)})
            if row and row["corrective_action_id"]:
                action = connection.execute(
                    "SELECT * FROM corrective_actions WHERE id = ? AND project_id = ?",
                    (row["corrective_action_id"], project_id),
                ).fetchone()
                if action:
                    links.append({"type": "corrective_action", **_row(action)})
            history = [
                _row(item)
                for item in connection.execute(
                    """
                    SELECT * FROM not_met_reconciliation_history
                    WHERE project_id = ? AND assessment_id = ? AND record_id = ?
                    ORDER BY changed_at, id
                    """,
                    (project_id, assessment_id, record_id),
                ).fetchall()
            ]
            note = connection.execute(
                "SELECT note FROM record_notes WHERE assessment_id = ? AND record_id = ?",
                (assessment_id, record_id),
            ).fetchone()
            determination = connection.execute(
                "SELECT status FROM determinations WHERE assessment_id = ? AND record_id = ?",
                (assessment_id, record_id),
            ).fetchone()
            evidence_references = [
                _row(item)
                for item in connection.execute(
                    """
                    SELECT em.id AS mapping_id, em.artifact_id, ea.name,
                           ea.relative_path, em.rationale, em.review_state,
                           ev.id AS version_id, ev.version_number, ev.sha256
                    FROM evidence_mappings em
                    JOIN evidence_artifacts ea ON ea.id = em.artifact_id
                    JOIN evidence_versions ev ON ev.id = em.evidence_version_id
                    WHERE em.target_type = 'assessment_record'
                      AND em.assessment_id = ? AND em.record_id = ?
                    ORDER BY em.created_at
                    """,
                    (assessment_id, record_id),
                ).fetchall()
            ]
            return {
                "state": "reconciled" if row else "unresolved",
                "outcome": row["outcome"] if row else None,
                "finding_id": row["finding_id"] if row else None,
                "corrective_action_id": row["corrective_action_id"] if row else None,
                "prefill": {
                    "citation": record["citation"],
                    "requirement_title": record["title"],
                    "determination_status": determination["status"] if determination else "",
                    "notes": note["note"] if note else "",
                    "recommendation": None,
                    "risk_rating": None,
                    "finding_title": f"Not Met: {record['citation']} {record['title']}",
                    "action_title": f"Remediate: {record_id}",
                },
                "evidence_references": evidence_references,
                "links": links,
                "history": history,
            }

    @app.put(
        "/api/projects/{project_id}/assessments/{assessment_id}/records/{record_id}/reconciliation"
    )
    def save_reconciliation(
        project_id: str,
        assessment_id: str,
        record_id: str,
        payload: ReconciliationSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
            _record_or_404(connection, assessment_id, record_id)
            determination = connection.execute(
                "SELECT status FROM determinations WHERE assessment_id=? AND record_id=?",
                (assessment_id, record_id),
            ).fetchone()
            if determination is None or determination["status"] != "Not Met":
                raise HTTPException(
                    422, "Reconciliation is only available for a current Not Met determination"
                )
            _user_or_422(connection, payload.actor_id)
            if payload.outcome not in {"create", "link_existing", "not_needed"}:
                raise HTTPException(422, "Unknown reconciliation outcome")
            if payload.outcome == "not_needed" and not payload.rationale.strip():
                raise HTTPException(422, "not_needed requires a rationale")
            old = connection.execute(
                """
                SELECT * FROM not_met_reconciliations
                WHERE project_id = ? AND assessment_id = ? AND record_id = ?
                """,
                (project_id, assessment_id, record_id),
            ).fetchone()
            finding_id, action_id = payload.finding_id, payload.corrective_action_id
            if payload.outcome == "create" and (
                not payload.title.strip() or not payload.action_title.strip()
            ):
                raise HTTPException(
                    422, "create requires explicit finding and corrective action titles"
                )
            if payload.outcome == "create":
                stamp = now()
                if old and old["finding_id"] and old["corrective_action_id"]:
                    finding_id = old["finding_id"]
                    action_id = old["corrective_action_id"]
                    connection.execute(
                        """
                        UPDATE findings SET title = ?, description = ?, updated_at = ?
                        WHERE id = ? AND project_id = ?
                        """,
                        (
                            payload.title.strip(),
                            payload.description.strip(),
                            stamp,
                            finding_id,
                            project_id,
                        ),
                    )
                    connection.execute(
                        """
                        UPDATE corrective_actions
                        SET title = ?, description = ?, updated_at = ?
                        WHERE id = ? AND project_id = ?
                        """,
                        (
                            payload.action_title.strip(),
                            payload.action_description.strip(),
                            stamp,
                            action_id,
                            project_id,
                        ),
                    )
                else:
                    finding_id, action_id = str(uuid4()), str(uuid4())
                    connection.execute(
                        """
                        INSERT INTO findings(
                            id, project_id, title, description, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            finding_id,
                            project_id,
                            payload.title.strip(),
                            payload.description.strip(),
                            stamp,
                            stamp,
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO corrective_actions(
                            id, project_id, finding_id, title, description,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            action_id,
                            project_id,
                            finding_id,
                            payload.action_title.strip(),
                            payload.action_description.strip(),
                            stamp,
                            stamp,
                        ),
                    )
            elif payload.outcome == "link_existing":
                if not finding_id or not action_id:
                    raise HTTPException(
                        422, "link_existing requires finding_id and corrective_action_id"
                    )
                valid = connection.execute(
                    """
                    SELECT 1
                    FROM findings f
                    JOIN corrective_actions a
                      ON a.finding_id = f.id AND a.project_id = f.project_id
                    WHERE f.id = ? AND a.id = ? AND f.project_id = ?
                    """,
                    (finding_id, action_id, project_id),
                ).fetchone()
                if valid is None:
                    raise HTTPException(
                        422, "Finding and corrective action must belong to this project"
                    )
                existing_link = connection.execute(
                    """
                    SELECT assessment_id, record_id FROM not_met_reconciliations
                    WHERE project_id = ? AND corrective_action_id = ?
                      AND NOT (assessment_id = ? AND record_id = ?)
                    """,
                    (project_id, action_id, assessment_id, record_id),
                ).fetchone()
                if existing_link is not None:
                    raise HTTPException(
                        409,
                        "Corrective action is already linked to another assessment record",
                    )
            if old and all(
                old[k] == v
                for k, v in {
                    "outcome": payload.outcome,
                    "finding_id": finding_id,
                    "corrective_action_id": action_id,
                    "rationale": payload.rationale.strip(),
                }.items()
            ):
                links = []
                for table, entity_id, entity_type in (
                    ("findings", finding_id, "finding"),
                    ("corrective_actions", action_id, "corrective_action"),
                ):
                    if entity_id:
                        linked = connection.execute(
                            f"SELECT * FROM {table} WHERE id = ? AND project_id = ?",
                            (entity_id, project_id),
                        ).fetchone()
                        if linked:
                            links.append({"type": entity_type, **_row(linked)})
                history = [
                    _row(item)
                    for item in connection.execute(
                        """
                        SELECT * FROM not_met_reconciliation_history
                        WHERE reconciliation_id = ? ORDER BY changed_at, id
                        """,
                        (old["id"],),
                    ).fetchall()
                ]
                return {
                    **_row(old),
                    "state": "reconciled",
                    "links": links,
                    "history": history,
                }
            stamp = now()
            rid = old["id"] if old else str(uuid4())
            connection.execute(
                """
                INSERT INTO not_met_reconciliations(
                    id, project_id, assessment_id, record_id, outcome,
                    finding_id, corrective_action_id, rationale, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assessment_id, record_id) DO UPDATE SET
                    outcome = excluded.outcome,
                    finding_id = excluded.finding_id,
                    corrective_action_id = excluded.corrective_action_id,
                    rationale = excluded.rationale,
                    updated_at = excluded.updated_at
                """,
                (
                    rid,
                    project_id,
                    assessment_id,
                    record_id,
                    payload.outcome,
                    finding_id,
                    action_id,
                    payload.rationale.strip(),
                    stamp,
                    stamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO not_met_reconciliation_history(
                    id, reconciliation_id, project_id, assessment_id, record_id,
                    outcome, finding_id, corrective_action_id, rationale,
                    actor_id, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    rid,
                    project_id,
                    assessment_id,
                    record_id,
                    payload.outcome,
                    finding_id,
                    action_id,
                    payload.rationale.strip(),
                    payload.actor_id,
                    stamp,
                ),
            )
            _audit(
                connection,
                "not_met_reconciliation.saved",
                "not_met_reconciliation",
                rid,
                {
                    "assessment_id": assessment_id,
                    "record_id": record_id,
                    "outcome": payload.outcome,
                },
                payload.actor_id,
            )
            saved = connection.execute(
                "SELECT * FROM not_met_reconciliations WHERE id = ?", (rid,)
            ).fetchone()
            assert saved is not None
            links = []
            if finding_id:
                finding = connection.execute(
                    "SELECT * FROM findings WHERE id = ? AND project_id = ?",
                    (finding_id, project_id),
                ).fetchone()
                if finding:
                    links.append({"type": "finding", **_row(finding)})
            if action_id:
                action = connection.execute(
                    "SELECT * FROM corrective_actions WHERE id = ? AND project_id = ?",
                    (action_id, project_id),
                ).fetchone()
                if action:
                    links.append({"type": "corrective_action", **_row(action)})
            history = [
                _row(item)
                for item in connection.execute(
                    """
                    SELECT * FROM not_met_reconciliation_history
                    WHERE reconciliation_id = ? ORDER BY changed_at, id
                    """,
                    (rid,),
                ).fetchall()
            ]
            return {
                **_row(saved),
                "state": "reconciled",
                "links": links,
                "history": history,
            }

    @app.put("/api/projects/{project_id}/corrective-actions/{action_id}")
    def save_corrective_action_state(
        project_id: str,
        action_id: str,
        payload: CorrectiveActionStateSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        transitions = {
            "Draft": {"Draft", "Open", "Withdrawn"},
            "Open": {"Open", "In Progress", "Waiting", "Ready for Validation", "Withdrawn"},
            "In Progress": {
                "Open",
                "In Progress",
                "Waiting",
                "Ready for Validation",
                "Withdrawn",
            },
            "Waiting": {"Open", "In Progress", "Waiting", "Ready for Validation", "Withdrawn"},
            "Ready for Validation": {"Ready for Validation", "Withdrawn"},
            "Closed": {"Closed"},
            "Withdrawn": {"Withdrawn"},
        }
        if payload.state not in transitions:
            raise HTTPException(422, "Unknown corrective action state")
        with database.connect() as connection:
            action = connection.execute(
                "SELECT * FROM corrective_actions WHERE id = ? AND project_id = ?",
                (action_id, project_id),
            ).fetchone()
            if action is None:
                raise HTTPException(404, "Corrective action not found")
            if payload.state not in transitions.get(action["status"], set()):
                raise HTTPException(422, "Corrective action state transition is not permitted")
            _user_or_422(connection, payload.actor_id)
            stamp = now()
            validation_state = (
                "Ready" if payload.state == "Ready for Validation" else action["validation_state"]
            )
            connection.execute(
                """
                UPDATE corrective_actions
                SET status = ?, validation_state = ?, updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (payload.state, validation_state, stamp, action_id, project_id),
            )
            _audit(
                connection,
                "corrective_action.state_changed",
                "corrective_action",
                action_id,
                {"project_id": project_id, "state": payload.state},
                payload.actor_id,
            )
            saved = connection.execute(
                "SELECT * FROM corrective_actions WHERE id = ? AND project_id = ?",
                (action_id, project_id),
            ).fetchone()
            assert saved is not None
            return _row(saved)

    validation_path = (
        "/api/projects/{project_id}/assessments/{assessment_id}/records/{record_id}"
        "/corrective-actions/{action_id}/validation"
    )

    @app.post(validation_path)
    def validate_corrective_action(
        project_id: str,
        assessment_id: str,
        record_id: str,
        action_id: str,
        payload: ValidationSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        if payload.outcome not in {"Validated", "Failed"}:
            raise HTTPException(422, "Validation outcome must be Validated or Failed")
        if not payload.notes.strip():
            raise HTTPException(422, "Validation notes are required")
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
            _user_or_422(connection, payload.actor_id)
            action = connection.execute(
                "SELECT * FROM corrective_actions WHERE id = ? AND project_id = ?",
                (action_id, project_id),
            ).fetchone()
            if action is None:
                raise HTTPException(404, "Corrective action not found")
            reconciliation = connection.execute(
                """
                SELECT finding_id FROM not_met_reconciliations
                WHERE project_id = ? AND assessment_id = ? AND record_id = ?
                  AND corrective_action_id = ? AND outcome IN ('create','link_existing')
                """,
                (project_id, assessment_id, record_id, action_id),
            ).fetchone()
            if reconciliation is None:
                raise HTTPException(422, "Corrective action is not linked to this assessed record")
            determination = connection.execute(
                """
                SELECT status, interview_observation FROM determinations
                WHERE assessment_id = ? AND record_id = ?
                """,
                (assessment_id, record_id),
            ).fetchone()
            if determination is None:
                raise HTTPException(422, "Determination is required before validation")
            if determination["status"] != "Not Met":
                raise HTTPException(422, "Validation requires a current Not Met determination")
            if action["status"] != "Ready for Validation":
                raise HTTPException(422, "Corrective action must be Ready for Validation")
            evidence_rows = connection.execute(
                """
                SELECT em.id AS mapping_id, em.artifact_id, em.evidence_version_id,
                       em.rationale, em.review_state, ev.sha256, ev.version_number
                FROM evidence_mappings em
                JOIN evidence_artifacts ea
                  ON ea.id = em.artifact_id AND ea.project_id = ?
                JOIN evidence_versions ev
                  ON ev.id = em.evidence_version_id
                 AND ev.artifact_id = ea.id AND ev.project_id = ea.project_id
                WHERE em.target_type = 'assessment_record'
                  AND em.assessment_id = ? AND em.record_id = ?
                ORDER BY em.created_at, em.id
                """,
                (project_id, assessment_id, record_id),
            ).fetchall()
            if payload.outcome == "Validated":
                has_interview = bool(
                    (determination["interview_observation"] or "").strip()
                )
                if not evidence_rows and not has_interview:
                    raise HTTPException(
                        422,
                        "Validated requires mapped evidence or documented interview/observation",
                    )
            revision = connection.execute(
                """
                SELECT revision_number FROM assessment_revisions
                WHERE assessment_id = ? AND project_id = ?
                """,
                (assessment_id, project_id),
            ).fetchone()
            assert revision is not None
            stamp = now()
            event_id = str(uuid4())
            evidence_context = {
                "presented": [_row(row) for row in evidence_rows],
                "interview_observation": determination["interview_observation"] or "",
            }
            connection.execute(
                """
                INSERT INTO validation_events(
                    id, project_id, assessment_id, assessment_revision, record_id,
                    finding_id, corrective_action_id, prior_determination,
                    prior_work_state, outcome, notes, actor_id, created_at,
                    evidence_context_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    assessment_id,
                    revision["revision_number"],
                    record_id,
                    reconciliation["finding_id"],
                    action_id,
                    determination["status"],
                    action["status"],
                    payload.outcome,
                    payload.notes.strip(),
                    payload.actor_id,
                    stamp,
                    json.dumps(evidence_context),
                ),
            )
            if payload.outcome == "Validated":
                connection.execute(
                    """
                    UPDATE determinations SET status = 'Met', updated_at = ?
                    WHERE assessment_id = ? AND record_id = ?
                    """,
                    (stamp, assessment_id, record_id),
                )
                connection.execute(
                    """
                    UPDATE corrective_actions
                    SET status = 'Closed', validation_state = 'Validated', updated_at = ?
                    WHERE id = ? AND project_id = ?
                    """,
                    (stamp, action_id, project_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE corrective_actions
                    SET status = 'In Progress', validation_state = 'Failed', updated_at = ?
                    WHERE id = ? AND project_id = ?
                    """,
                    (stamp, action_id, project_id),
                )
            if payload.outcome == "Validated":
                connection.execute(
                    """
                    INSERT INTO determination_history(
                        id, project_id, assessment_id, record_id, prior_status,
                        new_status, actor_id, created_at, validation_event_id
                    ) VALUES (?, ?, ?, ?, ?, 'Met', ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        project_id,
                        assessment_id,
                        record_id,
                        determination["status"],
                        payload.actor_id,
                        stamp,
                        event_id,
                    ),
                )
            _audit(
                connection,
                "corrective_action.validation",
                "validation_event",
                event_id,
                {
                    "project_id": project_id,
                    "assessment_id": assessment_id,
                    "record_id": record_id,
                    "outcome": payload.outcome,
                },
                payload.actor_id,
            )
            saved = connection.execute(
                "SELECT * FROM validation_events WHERE id = ? AND project_id = ?",
                (event_id, project_id),
            ).fetchone()
            assert saved is not None
            result = _row(saved)
            result["evidence_context"] = json.loads(result.pop("evidence_context_json"))
            return result

    @app.get(validation_path)
    def list_validations(
        project_id: str,
        assessment_id: str,
        record_id: str,
        action_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
            reconciliation = connection.execute(
                """
                SELECT r.*, f.title AS finding_title, f.description AS finding_description,
                       f.status AS finding_status, a.title AS action_title,
                       a.description AS action_description, a.status AS action_status,
                       a.validation_state
                FROM not_met_reconciliations r
                JOIN findings f ON f.id = r.finding_id AND f.project_id = r.project_id
                JOIN corrective_actions a
                  ON a.id = r.corrective_action_id
                 AND a.finding_id = f.id AND a.project_id = f.project_id
                WHERE r.project_id = ? AND r.assessment_id = ? AND r.record_id = ?
                  AND r.corrective_action_id = ?
                """,
                (project_id, assessment_id, record_id, action_id),
            ).fetchone()
            if reconciliation is None:
                raise HTTPException(404, "Corrective action validation context not found")
            determination = connection.execute(
                """
                SELECT status, interview_observation FROM determinations
                WHERE assessment_id = ? AND record_id = ?
                """,
                (assessment_id, record_id),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT * FROM validation_events
                WHERE project_id = ? AND assessment_id = ? AND record_id = ?
                  AND corrective_action_id = ?
                ORDER BY created_at, id
                """,
                (project_id, assessment_id, record_id, action_id),
            ).fetchall()
            events = []
            for row in rows:
                event = _row(row)
                event["evidence_context"] = json.loads(event.pop("evidence_context_json"))
                events.append(event)
            return {
                "finding": {
                    "id": reconciliation["finding_id"],
                    "title": reconciliation["finding_title"],
                    "description": reconciliation["finding_description"],
                    "status": reconciliation["finding_status"],
                },
                "corrective_action": {
                    "id": reconciliation["corrective_action_id"],
                    "title": reconciliation["action_title"],
                    "description": reconciliation["action_description"],
                    "status": reconciliation["action_status"],
                    "validation_state": reconciliation["validation_state"],
                },
                "determination": _row(determination) if determination else None,
                "events": events,
            }

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
        uploaded_file_id = str(uuid4())
        content = await file.read()
        if not file.filename:
            raise HTTPException(status_code=422, detail="Evidence filename is required")
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            relative_path = file_storage.save(project_id, artifact_id, file.filename, content)
            created_at = now()
            version = {
                "id": str(uuid4()),
                "project_id": project_id,
                "version_number": 1,
                "sha256": sha256(file_storage.read(relative_path)).hexdigest(),
                "relative_path": relative_path,
                "created_at": created_at,
            }
            connection.execute(
                """
                INSERT INTO evidence_artifacts(
                    id, project_id, name, relative_path, created_at, uploaded_file_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    project_id,
                    file.filename,
                    relative_path,
                    created_at,
                    uploaded_file_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO evidence_versions(
                    id, artifact_id, project_id, version_number, relative_path, sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version["id"],
                    artifact_id,
                    version["project_id"],
                    version["version_number"],
                    version["relative_path"],
                    version["sha256"],
                    version["created_at"],
                ),
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
            "uploaded_file_id": uploaded_file_id,
            "version": version,
        }

    @app.get("/api/projects/{project_id}/evidence")
    def list_evidence(
        project_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            _project_or_404(connection, project_id)
            return [
                {
                    **_row(row),
                    "shared_record_count": connection.execute(
                        "SELECT COUNT(*) AS count FROM evidence_mappings "
                        "WHERE artifact_id = ? AND target_type = 'assessment_record'",
                        (row["id"],),
                    ).fetchone()["count"],
                }
                for row in connection.execute(
                    """
                    SELECT ea.*, ev.id AS version_id, ev.project_id AS version_project_id,
                           ev.version_number, ev.sha256,
                           ev.relative_path AS version_relative_path,
                           ev.created_at AS version_created_at
                    FROM evidence_artifacts ea
                    JOIN evidence_versions ev
                      ON ev.artifact_id = ea.id AND ev.version_number = 1
                    WHERE ea.project_id = ?
                    ORDER BY ea.created_at
                    """,
                    (project_id,),
                )
            ]

    @app.post(
        "/api/projects/{project_id}/assessments/{assessment_id}/evidence-mappings",
        status_code=201,
    )
    def create_mapping(
        project_id: str,
        assessment_id: str,
        payload: EvidenceMappingCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        mapping_id = str(uuid4())
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
            _record_or_404(connection, assessment_id, payload.record_id)
            artifact = connection.execute(
                """
                SELECT ea.id
                FROM evidence_artifacts ea
                WHERE ea.project_id = ? AND ea.id = ?
                """,
                (project_id, payload.artifact_id),
            ).fetchone()
            if artifact is None:
                raise HTTPException(status_code=404, detail="Evidence artifact not found")
            try:
                connection.execute(
                    """
                    INSERT INTO evidence_mappings(
                        id, project_id, artifact_id, evidence_version_id, target_type,
                        assessment_id, record_id, profile_version_id, target_key,
                        rationale, review_state, created_at
                    ) VALUES (?, ?, ?, ?, 'assessment_record', ?, ?, NULL, NULL,
                              ?, 'Not reviewed', ?)
                    """,
                    (
                        mapping_id,
                        project_id,
                        payload.artifact_id,
                        connection.execute(
                            "SELECT id FROM evidence_versions "
                            "WHERE artifact_id = ? AND project_id = ? "
                            "ORDER BY version_number DESC LIMIT 1",
                            (payload.artifact_id, project_id),
                        ).fetchone()["id"],
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
            shared_count = connection.execute(
                "SELECT COUNT(*) AS count FROM evidence_mappings "
                "WHERE artifact_id = ? AND target_type = 'assessment_record'",
                (payload.artifact_id,),
            ).fetchone()["count"]
        return {
            "id": mapping_id,
            "artifact_id": payload.artifact_id,
            "record_id": payload.record_id,
            "rationale": payload.rationale.strip(),
            "review_state": "Not reviewed",
            "shared_record_count": shared_count,
        }

    @app.delete(
        "/api/projects/{project_id}/assessments/{assessment_id}/evidence-mappings/{mapping_id}"
    )
    def delete_mapping(
        project_id: str,
        assessment_id: str,
        mapping_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, bool]:
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
            mapping = connection.execute(
                """
                SELECT em.*
                FROM evidence_mappings em
                JOIN evidence_artifacts ea ON ea.id = em.artifact_id
                WHERE em.target_type = 'assessment_record'
                  AND em.assessment_id = ? AND em.id = ? AND ea.project_id = ?
                """,
                (assessment_id, mapping_id, project_id),
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
                WHERE target_type = 'assessment_record'
                  AND assessment_id = ? AND record_id = ?
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

    @app.get("/api/projects/{project_id}/assessments/{assessment_id}/audit")
    def list_audit(
        project_id: str,
        assessment_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            _assessment_for_project_or_404(connection, project_id, assessment_id)
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

    def sra_declaration(connection: Any, project_id: str) -> tuple[Any, dict[str, Any]]:
        project = _project_or_404(connection, project_id)
        framework = connection.execute(
            "SELECT declarations_json FROM framework_versions WHERE id = ?",
            (project["framework_version_id"],),
        ).fetchone()
        declaration = json.loads(framework["declarations_json"]).get("sra")
        if not declaration:
            raise HTTPException(status_code=404, detail="SRA is not declared for this framework")
        return project, cast(dict[str, Any], declaration)

    def approved_profile_or_409(connection: Any, project: Any) -> Any:
        version_id = project["active_profile_version_id"]
        if not version_id or _profile_status(connection, version_id) != "Approved":
            raise HTTPException(
                status_code=409,
                detail="Approve a Profile version before completing the SRA",
            )
        return _profile_version_or_404(connection, project["id"], version_id)

    def sra_scope_inventory(
        connection: Any,
        project_id: str,
        profile_version_id: str,
        declaration: dict[str, Any],
    ) -> list[dict[str, Any]]:
        inventory: list[dict[str, Any]] = []
        for target in declaration["scope_targets"]:
            scope_type = cast(str, target["scope_type"])
            item_types = cast(list[str], target.get("profile_item_types", []))
            if item_types:
                placeholders = ",".join("?" for _ in item_types)
                rows = connection.execute(
                    f"""
                    SELECT items.client_key,
                           COALESCE(MAX(CASE WHEN field_values.field_key = 'name'
                                             THEN field_values.value END),
                                    items.client_key) AS name
                    FROM profile_items items
                    LEFT JOIN profile_field_values field_values
                      ON field_values.profile_item_id = items.id
                     AND field_values.profile_version_id = items.profile_version_id
                    WHERE items.profile_version_id = ?
                      AND items.item_type IN ({placeholders})
                    GROUP BY items.id, items.client_key, items.sort_order
                    ORDER BY items.sort_order
                    """,
                    (profile_version_id, *item_types),
                ).fetchall()
                inventory.extend(
                    {
                        "scope_type": scope_type,
                        "target_key": f"item:{row['client_key']}",
                        "name": row["name"],
                    }
                    for row in rows
                )
            sections = cast(list[str], target.get("profile_sections", []))
            if sections:
                placeholders = ",".join("?" for _ in sections)
                rows = connection.execute(
                    f"""
                    SELECT section, field_key, label, value, sort_order
                    FROM profile_field_values
                    WHERE profile_version_id = ? AND profile_item_id IS NULL
                      AND section IN ({placeholders}) AND trim(value) != ''
                    ORDER BY sort_order
                    """,
                    (profile_version_id, *sections),
                ).fetchall()
                inventory.extend(
                    {
                        "scope_type": scope_type,
                        "target_key": f"field:{row['section']}:{row['field_key']}",
                        "name": row["value"] or row["label"],
                    }
                    for row in rows
                )
        reviews = {
            (row["scope_type"], row["target_key"]): row
            for row in connection.execute(
                """
                SELECT * FROM sra_scope_reviews
                WHERE project_id = ? AND profile_version_id = ?
                """,
                (project_id, profile_version_id),
            )
        }
        return [
            item
            | (
                _row(reviews[(item["scope_type"], item["target_key"])])
                if (item["scope_type"], item["target_key"]) in reviews
                else {
                    "id": None,
                    "included": None,
                    "exclusion_rationale": "",
                    "reviewed_by": "",
                    "reviewed_at": None,
                }
            )
            for item in inventory
        ]

    def risk_result(connection: Any, row: Any) -> dict[str, Any]:
        evidence = [
            _row(mapping)
            for mapping in connection.execute(
                """
                SELECT mappings.*, artifacts.name, versions.version_number,
                       versions.sha256, versions.relative_path
                FROM risk_evidence_mappings mappings
                JOIN evidence_artifacts artifacts
                  ON artifacts.id = mappings.artifact_id
                 AND artifacts.project_id = mappings.project_id
                JOIN evidence_versions versions
                  ON versions.id = mappings.evidence_version_id
                 AND versions.artifact_id = mappings.artifact_id
                 AND versions.project_id = mappings.project_id
                WHERE mappings.risk_id = ? AND mappings.project_id = ?
                ORDER BY mappings.created_at
                """,
                (row["id"], row["project_id"]),
            )
        ]
        return _row(row) | {
            "inherent": score_risk(row["inherent_likelihood"], row["inherent_impact"]),
            "residual": score_risk(row["residual_likelihood"], row["residual_impact"]),
            "evidence_links": evidence,
        }

    def validate_risk(
        connection: Any, project_id: str, payload: RiskSave
    ) -> tuple[RiskScore, RiskScore]:
        project, declaration = sra_declaration(connection, project_id)
        approved = approved_profile_or_409(connection, project)
        actor = _user_or_422(connection, payload.actor_id)
        payload.reviewed_by = actor["display_name"]
        if payload.profile_version_id != approved["id"]:
            raise HTTPException(
                status_code=422, detail="Risk must use the approved Profile version"
            )
        _assessment_for_project_or_404(connection, project_id, payload.assessment_id)
        active = connection.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if active is None or payload.assessment_id != active["assessment_id"]:
            raise HTTPException(
                status_code=422, detail="Risk must use the project's active assessment"
            )
        if payload.treatment not in {"corrective_action", "acceptance"}:
            raise HTTPException(status_code=422, detail="Unknown risk treatment")
        for value, label in (
            (payload.reviewed_at, "reviewed_at"),
            (payload.review_date, "review_date"),
            (payload.approved_at, "approved_at"),
        ):
            if value:
                try:
                    if label == "review_date":
                        date.fromisoformat(value)
                    else:
                        datetime.fromisoformat(value)
                except ValueError as error:
                    raise HTTPException(
                        status_code=422, detail=f"{label} must be ISO-8601"
                    ) from error
        inherent = score_risk(payload.inherent_likelihood, payload.inherent_impact)
        residual = score_risk(payload.residual_likelihood, payload.residual_impact)
        values = payload.model_dump(exclude={"actor_id"})
        missing_required = [
            field for field in declaration["risk_required_fields"] if not values.get(field)
        ]
        if missing_required:
            raise HTTPException(
                status_code=422,
                detail="Risk requires " + ", ".join(missing_required),
            )
        if payload.treatment == "acceptance":
            missing = [
                field
                for field in declaration["acceptance_required_fields"]
                if not values.get(field)
            ]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail="Risk acceptance requires " + ", ".join(missing),
                )
        bands = {inherent["band"], residual["band"]}
        if payload.treatment == "acceptance" and bands & set(
            declaration["approval_required_bands"]
        ):
            missing = [
                field for field in declaration["approval_required_fields"] if not values.get(field)
            ]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail="High or Critical risk requires " + ", ".join(missing),
                )
        return inherent, residual

    def sra_workspace(connection: Any, project_id: str) -> dict[str, Any]:
        project, declaration = sra_declaration(connection, project_id)
        approved = approved_profile_or_409(connection, project)
        anchor = connection.execute(
            """
            SELECT record_id, citation, title, regulation_text, work_area
            FROM framework_records
            WHERE framework_version_id = ? AND record_id = ?
            """,
            (project["framework_version_id"], declaration["anchor_record_id"]),
        ).fetchone()
        if anchor is None:
            raise HTTPException(status_code=409, detail="Declared SRA anchor does not resolve")
        scope = sra_scope_inventory(connection, project_id, approved["id"], declaration)
        risks = [
            risk_result(connection, row)
            for row in connection.execute(
                "SELECT * FROM risks WHERE project_id = ? ORDER BY created_at, id",
                (project_id,),
            )
        ]
        blockers = [
            f"Review {item['scope_type']} scope: {item['name']}"
            for item in scope
            if item["included"] is None
        ]
        if not scope:
            blockers.append("Approved Profile contains no declared ePHI scope facts")
        if not risks:
            blockers.append("Record at least one complete threat-vulnerability risk")
        complete_count = sum(item["included"] is not None for item in scope) + len(risks)
        total_count = len(scope) + max(1, len(risks))
        percentage = round(100 * complete_count / total_count) if total_count else 0
        active_assessment = connection.execute(
            """
            SELECT assessment_id AS id
            FROM project_active_assessments WHERE project_id = ?
            """,
            (project_id,),
        ).fetchone()
        return {
            "project_id": project_id,
            "assessment_id": active_assessment["id"] if active_assessment else None,
            "work_area": declaration["work_area"],
            "anchor": _row(anchor),
            "profile_version_id": approved["id"],
            "scope_items": scope,
            "risks": risks,
            "blockers": blockers,
            "status": "Complete" if not blockers else "Incomplete",
            "completion": {
                "complete": not blockers,
                "percentage": percentage,
                "missing": blockers,
            },
        }

    @app.get("/api/projects/{project_id}/sra")
    def get_sra(project_id: str, database: Annotated[Database, Depends(db)]) -> dict[str, Any]:
        with database.connect() as connection:
            return sra_workspace(connection, project_id)

    @app.get("/api/projects/{project_id}/sra/scope")
    def list_sra_scope(
        project_id: str, database: Annotated[Database, Depends(db)]
    ) -> dict[str, Any]:
        with database.connect() as connection:
            workspace = sra_workspace(connection, project_id)
            return {
                "profile_version_id": workspace["profile_version_id"],
                "items": workspace["scope_items"],
                "complete": not any(item["included"] is None for item in workspace["scope_items"]),
            }

    @app.put("/api/projects/{project_id}/sra/scope")
    def save_sra_scope(
        project_id: str,
        payload: SRAScopeSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            project, declaration = sra_declaration(connection, project_id)
            approved = approved_profile_or_409(connection, project)
            actor = _user_or_422(connection, payload.actor_id)
            payload.reviewed_by = actor["display_name"]
            if payload.profile_version_id != approved["id"]:
                raise HTTPException(
                    status_code=422, detail="SRA scope must use the approved Profile version"
                )
            valid_targets = {
                (item["scope_type"], item["target_key"])
                for item in sra_scope_inventory(connection, project_id, approved["id"], declaration)
            }
            if (payload.scope_type, payload.target_key) not in valid_targets:
                raise HTTPException(status_code=404, detail="SRA scope target not found")
            if not payload.included and not payload.exclusion_rationale.strip():
                raise HTTPException(status_code=422, detail="Exclusion requires a rationale")
            stamp = now()
            connection.execute(
                """
                INSERT INTO sra_scope_reviews(
                    id, project_id, profile_version_id, scope_type, target_key,
                    included, exclusion_rationale, reviewed_by, reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, profile_version_id, scope_type, target_key)
                DO UPDATE SET included = excluded.included,
                              exclusion_rationale = excluded.exclusion_rationale,
                              reviewed_by = excluded.reviewed_by,
                              reviewed_at = excluded.reviewed_at
                """,
                (
                    str(uuid4()),
                    project_id,
                    approved["id"],
                    payload.scope_type,
                    payload.target_key,
                    int(payload.included),
                    payload.exclusion_rationale.strip(),
                    payload.reviewed_by.strip(),
                    stamp,
                ),
            )
            _audit(
                connection,
                "sra.scope_saved",
                "sra_scope",
                f"{project_id}:{payload.target_key}",
                {"project_id": project_id, "scope_type": payload.scope_type},
                payload.actor_id,
            )
            return sra_workspace(connection, project_id)

    @app.get("/api/projects/{project_id}/risks")
    def list_risks(
        project_id: str, database: Annotated[Database, Depends(db)]
    ) -> list[dict[str, Any]]:
        with database.connect() as connection:
            sra_declaration(connection, project_id)
            return [
                risk_result(connection, row)
                for row in connection.execute(
                    "SELECT * FROM risks WHERE project_id = ? ORDER BY created_at, id",
                    (project_id,),
                )
            ]

    @app.post("/api/projects/{project_id}/risks", status_code=201)
    def create_risk(
        project_id: str,
        payload: RiskSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            inherent, residual = validate_risk(connection, project_id, payload)
            risk_id, stamp = str(uuid4()), now()
            values = payload.model_dump(exclude={"actor_id"}) | {
                "id": risk_id,
                "project_id": project_id,
                "created_by": payload.actor_id,
                "created_at": stamp,
                "updated_at": stamp,
            }
            columns = ", ".join(values)
            parameters = ", ".join(f":{column}" for column in values)
            connection.execute(f"INSERT INTO risks({columns}) VALUES ({parameters})", values)
            _audit(
                connection,
                "risk.created",
                "risk",
                risk_id,
                {"project_id": project_id, "inherent": inherent, "residual": residual},
                payload.actor_id,
            )
            row = connection.execute(
                "SELECT * FROM risks WHERE id = ? AND project_id = ?",
                (risk_id, project_id),
            ).fetchone()
            return risk_result(connection, row)

    @app.get("/api/projects/{project_id}/risks/{risk_id}")
    def get_risk(
        project_id: str,
        risk_id: str,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            sra_declaration(connection, project_id)
            row = connection.execute(
                "SELECT * FROM risks WHERE id = ? AND project_id = ?",
                (risk_id, project_id),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Risk not found")
            return risk_result(connection, row)

    @app.put("/api/projects/{project_id}/risks/{risk_id}")
    def update_risk(
        project_id: str,
        risk_id: str,
        payload: RiskSave,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM risks WHERE id = ? AND project_id = ?",
                    (risk_id, project_id),
                ).fetchone()
                is None
            ):
                raise HTTPException(status_code=404, detail="Risk not found")
            validate_risk(connection, project_id, payload)
            values = payload.model_dump(exclude={"actor_id"}) | {
                "risk_id": risk_id,
                "project_id": project_id,
                "updated_at": now(),
            }
            update_columns = [
                column for column in values if column not in {"risk_id", "project_id"}
            ]
            assignments = ", ".join(f"{column} = :{column}" for column in update_columns)
            connection.execute(
                f"UPDATE risks SET {assignments} WHERE id = :risk_id AND project_id = :project_id",
                values,
            )
            _audit(
                connection,
                "risk.updated",
                "risk",
                risk_id,
                {"project_id": project_id},
                payload.actor_id,
            )
            row = connection.execute(
                "SELECT * FROM risks WHERE id = ? AND project_id = ?",
                (risk_id, project_id),
            ).fetchone()
            return risk_result(connection, row)

    @app.post(
        "/api/projects/{project_id}/risks/{risk_id}/evidence-mappings",
        status_code=201,
    )
    def create_risk_evidence_mapping(
        project_id: str,
        risk_id: str,
        payload: RiskEvidenceMappingCreate,
        database: Annotated[Database, Depends(db)],
    ) -> dict[str, Any]:
        with database.connect() as connection:
            _user_or_422(connection, payload.actor_id)
            if (
                connection.execute(
                    "SELECT 1 FROM risks WHERE id = ? AND project_id = ?",
                    (risk_id, project_id),
                ).fetchone()
                is None
            ):
                raise HTTPException(status_code=404, detail="Risk not found")
            evidence = connection.execute(
                """
                SELECT 1 FROM evidence_versions versions
                JOIN evidence_artifacts artifacts
                  ON artifacts.id = versions.artifact_id
                 AND artifacts.project_id = versions.project_id
                WHERE artifacts.id = ? AND versions.id = ?
                  AND artifacts.project_id = ? AND versions.project_id = ?
                """,
                (
                    payload.artifact_id,
                    payload.evidence_version_id,
                    project_id,
                    project_id,
                ),
            ).fetchone()
            if evidence is None:
                raise HTTPException(status_code=404, detail="Evidence artifact/version not found")
            mapping_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO risk_evidence_mappings(
                    id, project_id, risk_id, artifact_id, evidence_version_id,
                    rationale, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping_id,
                    project_id,
                    risk_id,
                    payload.artifact_id,
                    payload.evidence_version_id,
                    payload.rationale.strip(),
                    payload.actor_id,
                    now(),
                ),
            )
            _audit(
                connection,
                "risk.evidence_mapped",
                "risk_evidence_mapping",
                mapping_id,
                {"project_id": project_id, "risk_id": risk_id},
                payload.actor_id,
            )
            row = connection.execute(
                "SELECT * FROM risks WHERE id = ? AND project_id = ?",
                (risk_id, project_id),
            ).fetchone()
            return risk_result(connection, row)

    return app


app = create_app()
