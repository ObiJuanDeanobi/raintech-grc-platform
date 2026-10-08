"""Project evidence library, multi-objective mapping and staleness (GitHub issue #142).

Evidence is uploaded once per project and mapped to many assessment objectives;
each mapping keeps its own rationale (AC-007). Staleness is derived on read from
the artifact's review date and the project's warning lead time; it changes only
derived verification (``api.verification``), never a determination (AC-024).
"""

import sqlite3
from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from api import evidence_lifecycle
from api.database import active_assessment_for_project

_SEVERITY = {
    evidence_lifecycle.CURRENT: 0,
    evidence_lifecycle.DUE_SOON: 1,
    evidence_lifecycle.STALE: 2,
}


def _days_until(review_date: str | None, on: date) -> int | None:
    if not review_date:
        return None
    return (date.fromisoformat(review_date) - on).days


def review_fields(review_date: str | None, lead_days: int, on: date) -> dict[str, Any]:
    return {
        "review_status": evidence_lifecycle.review_status(review_date, lead_days, on),
        "days_until_review": _days_until(review_date, on),
    }


def library(
    connection: sqlite3.Connection, project_id: str, on: date | None = None
) -> dict[str, Any]:
    """Every live artifact with its status and the objectives that use it."""
    day = on or evidence_lifecycle.today()
    lead = evidence_lifecycle.lead_days(connection, project_id)
    assessment = active_assessment_for_project(connection, project_id)
    uses: dict[str, list[dict[str, Any]]] = {}
    if assessment is not None:
        for row in connection.execute(
            """SELECT m.id AS mapping_id, m.artifact_id, m.assessment_id, m.record_id,
                      m.rationale, m.review_state, m.created_at, ev.version_number,
                      r.citation, r.title, r.parent_id
               FROM evidence_mappings m
               JOIN evidence_versions ev ON ev.id = m.evidence_version_id
               JOIN framework_records r
                 ON r.framework_version_id = ? AND r.record_id = m.record_id
               WHERE m.project_id = ? AND m.assessment_id = ?
                 AND m.target_type = 'assessment_record'
               ORDER BY r.sort_order, r.record_id""",
            (assessment["framework_version_id"], project_id, assessment["id"]),
        ):
            uses.setdefault(row["artifact_id"], []).append(dict(row))
    other = {
        row["artifact_id"]: row["count"]
        for row in connection.execute(
            """SELECT artifact_id, COUNT(*) AS count FROM evidence_mappings
               WHERE project_id = ? AND target_type != 'assessment_record'
               GROUP BY artifact_id""",
            (project_id,),
        )
    }
    risk = {
        row["artifact_id"]: row["count"]
        for row in connection.execute(
            """SELECT artifact_id, COUNT(*) AS count FROM risk_evidence_mappings
               WHERE project_id = ? GROUP BY artifact_id""",
            (project_id,),
        )
    }
    artifacts = []
    for row in connection.execute(
        """SELECT ea.id, ea.name, ea.created_at, ea.review_date,
                  ev.id AS version_id, ev.version_number, ev.sha256,
                  ev.created_at AS version_created_at
           FROM evidence_artifacts ea
           JOIN evidence_versions ev
             ON ev.artifact_id = ea.id
            AND ev.version_number = (
                SELECT MAX(version_number) FROM evidence_versions WHERE artifact_id = ea.id)
           WHERE ea.project_id = ? AND ea.deleted_at IS NULL
           ORDER BY lower(ea.name), ea.created_at""",
        (project_id,),
    ):
        mappings = uses.get(row["id"], [])
        artifacts.append(
            {
                **dict(row),
                **review_fields(row["review_date"], lead, day),
                "used_by": mappings,
                "other_use_count": other.get(row["id"], 0) + risk.get(row["id"], 0),
            }
        )
    return {
        "today": day.isoformat(),
        "lead_days": lead,
        "assessment_id": assessment["id"] if assessment is not None else None,
        "artifacts": artifacts,
    }


def record_review_states(
    connection: sqlite3.Connection, assessment: Any, on: date | None = None
) -> dict[str, str]:
    """The worst review status of the evidence mapped to each record.

    Only records with due-soon or stale evidence appear, so callers can treat a
    missing key as current.
    """
    day = on or evidence_lifecycle.today()
    lead = evidence_lifecycle.lead_days(connection, assessment["project_id"])
    worst: dict[str, str] = {}
    for row in connection.execute(
        """SELECT m.record_id, ea.review_date FROM evidence_mappings m
           JOIN evidence_artifacts ea ON ea.id = m.artifact_id
           WHERE m.assessment_id = ? AND m.target_type = 'assessment_record'
             AND ea.deleted_at IS NULL AND ea.review_date IS NOT NULL""",
        (assessment["id"],),
    ):
        status = evidence_lifecycle.review_status(row["review_date"], lead, day)
        if _SEVERITY[status] > _SEVERITY.get(worst.get(row["record_id"], ""), 0):
            worst[row["record_id"]] = status
    return worst


def worst_of(statuses: list[str | None]) -> str | None:
    found = [status for status in statuses if status]
    return max(found, key=lambda status: _SEVERITY[status]) if found else None


def map_many(
    connection: sqlite3.Connection,
    project_id: str,
    assessment_id: str,
    artifact_id: str,
    record_ids: list[str],
    rationale: str,
    created_at: str,
) -> list[dict[str, Any]]:
    """Map one artifact to several determination records in one act.

    All or nothing: an unknown record, a record that already carries this
    artifact, or a binned artifact refuses the whole request. Each mapping is
    its own row with its own copy of the rationale, editable afterwards.
    """
    artifact = evidence_lifecycle.artifact_or_404(connection, project_id, artifact_id)
    if artifact["deleted_at"]:
        raise HTTPException(status_code=409, detail="Binned evidence cannot be mapped")
    ids = list(dict.fromkeys(record_ids))
    known = {
        row["record_id"]
        for row in connection.execute(
            f"""SELECT r.record_id FROM framework_records r
                JOIN assessments a ON a.framework_version_id = r.framework_version_id
                WHERE a.id = ? AND r.carries_determination = 1
                  AND r.record_id IN ({",".join("?" * len(ids))})""",
            (assessment_id, *ids),
        )
    }
    missing = [record_id for record_id in ids if record_id not in known]
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Evidence maps to assessment objectives only: " + ", ".join(missing),
        )
    already = [
        row["record_id"]
        for row in connection.execute(
            f"""SELECT record_id FROM evidence_mappings
                WHERE artifact_id = ? AND assessment_id = ?
                  AND target_type = 'assessment_record'
                  AND record_id IN ({",".join("?" * len(ids))})""",
            (artifact_id, assessment_id, *ids),
        )
    ]
    if already:
        raise HTTPException(
            status_code=409,
            detail="Evidence is already mapped to: " + ", ".join(sorted(already)),
        )
    version_id = evidence_lifecycle.versions(connection, artifact_id)[-1]["id"]
    created = []
    for record_id in ids:
        mapping = {
            "id": str(uuid4()),
            "artifact_id": artifact_id,
            "evidence_version_id": version_id,
            "record_id": record_id,
            "rationale": rationale,
            "review_state": "Not reviewed",
        }
        connection.execute(
            """INSERT INTO evidence_mappings(
                   id, project_id, artifact_id, evidence_version_id, target_type,
                   assessment_id, record_id, profile_version_id, target_key,
                   rationale, review_state, created_at
               ) VALUES (?, ?, ?, ?, 'assessment_record', ?, ?, NULL, NULL,
                         ?, 'Not reviewed', ?)""",
            (
                mapping["id"],
                project_id,
                artifact_id,
                version_id,
                assessment_id,
                record_id,
                rationale,
                created_at,
            ),
        )
        created.append(mapping)
    return created


def move_mappings_to(
    connection: sqlite3.Connection, project_id: str, artifact_id: str, version_id: str
) -> list[dict[str, Any]]:
    """Pin the active assessment's mappings of an artifact to ``version_id``.

    The same act as "Use latest version" (#119), applied to every mapping at
    once when a stale artifact is renewed. Earlier assessments keep the
    versions they were worked with. Returns the rows as they were before.
    """
    assessment = active_assessment_for_project(connection, project_id)
    if assessment is None:
        return []
    rows = [
        dict(row)
        for row in connection.execute(
            """SELECT id, evidence_version_id, record_id FROM evidence_mappings
               WHERE artifact_id = ? AND project_id = ? AND assessment_id = ?
                 AND target_type = 'assessment_record' AND evidence_version_id != ?""",
            (artifact_id, project_id, assessment["id"], version_id),
        )
    ]
    for row in rows:
        connection.execute(
            "UPDATE evidence_mappings SET evidence_version_id = ? WHERE id = ?",
            (version_id, row["id"]),
        )
    return rows


def assessment_mapping_or_404(
    connection: sqlite3.Connection, project_id: str, assessment_id: str, mapping_id: str
) -> Any:
    mapping = connection.execute(
        """SELECT * FROM evidence_mappings WHERE id = ? AND assessment_id = ?
           AND project_id = ? AND target_type = 'assessment_record'""",
        (mapping_id, assessment_id, project_id),
    ).fetchone()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Evidence mapping not found")
    return mapping
