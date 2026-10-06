"""Substantive reopening of the current issued HIPAA assessment (Issue #81)."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from api.correction import current_issuance
from api.database import active_assessment_for_project

SUBSTANTIVE = "substantive"

# Assessment-scoped state carried into the successor. Project-level work
# (findings, corrective actions, risks, evidence files) is referenced, never copied.
_CARRIED: tuple[tuple[str, bool], ...] = (
    ("determinations", False),
    ("record_notes", False),
    ("prompt_answers", False),
    ("prompt_placements", False),
    ("not_met_reconciliations", True),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _copy(
    connection: sqlite3.Connection,
    table: str,
    new_ids: bool,
    predecessor_id: str,
    successor_id: str,
    where: str = "",
) -> None:
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
    fresh_id = "lower(hex(randomblob(16)))"
    select = [
        "?" if name == "assessment_id" else (fresh_id if name == "id" and new_ids else name)
        for name in columns
    ]
    connection.execute(
        f"INSERT INTO {table}({','.join(columns)}) SELECT {','.join(select)} "
        f"FROM {table} WHERE assessment_id=? {where}",
        (successor_id, predecessor_id),
    )


def reopening_for(connection: sqlite3.Connection, assessment_id: str) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM assessment_reopenings WHERE successor_assessment_id=?",
            (assessment_id,),
        ).fetchone(),
    )


def revalidation_items(connection: sqlite3.Connection, assessment_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM revalidation_items WHERE assessment_id=? ORDER BY record_id",
            (assessment_id,),
        )
    ]


def reopen_assessment(
    connection: sqlite3.Connection,
    project_id: str,
    prior_package_id: str,
    classification: str,
    affected_record_ids: list[str],
    rationale: str,
    actor_id: str,
) -> dict[str, Any]:
    if classification != SUBSTANTIVE:
        raise ValueError("Reopening must be explicitly classified as substantive")
    if not rationale.strip():
        raise ValueError("A reopening rationale is required")
    affected = sorted(set(affected_record_ids))
    if not affected:
        raise ValueError("Select at least one affected record")
    connection.execute("BEGIN IMMEDIATE")
    package = connection.execute(
        "SELECT * FROM generated_packages WHERE id=? AND project_id=?",
        (prior_package_id, project_id),
    ).fetchone()
    active = active_assessment_for_project(connection, project_id)
    if package is None or active is None or package["assessment_id"] != active["id"]:
        raise LookupError("Package not found")
    current = current_issuance(connection, project_id)
    if current is None or current["package_id"] != prior_package_id:
        raise ValueError("Only the current issued package can be reopened")
    known = {
        row[0]
        for row in connection.execute(
            """SELECT record_id FROM framework_records
               WHERE framework_version_id=? AND carries_determination=1""",
            (active["framework_version_id"],),
        )
    }
    unknown = [record for record in affected if record not in known]
    if unknown:
        raise ValueError("Unknown affected records: " + ", ".join(unknown))
    predecessor_id, successor_id, created = active["id"], str(uuid4()), _now()
    connection.execute(
        """INSERT INTO assessments(id, project_id, framework_version_id, created_at)
           VALUES (?,?,?,?)""",
        (successor_id, project_id, active["framework_version_id"], created),
    )
    for table, new_ids in _CARRIED:
        _copy(connection, table, new_ids, predecessor_id, successor_id)
    # Evidence mappings keep their EvidenceVersion identity and rationale.
    _copy(
        connection,
        "evidence_mappings",
        True,
        predecessor_id,
        successor_id,
        "AND target_type='assessment_record'",
    )
    reopening_id = str(uuid4())
    connection.execute(
        """INSERT INTO assessment_reopenings(
          id, project_id, classification, rationale, affected_record_ids_json,
          predecessor_assessment_id, successor_assessment_id, prior_package_id,
          prior_issuance_id, actor_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            reopening_id,
            project_id,
            SUBSTANTIVE,
            rationale.strip(),
            json.dumps(affected),
            predecessor_id,
            successor_id,
            prior_package_id,
            current["id"],
            actor_id,
            created,
        ),
    )
    for record_id in affected:
        connection.execute(
            """INSERT INTO revalidation_items(
                 id, project_id, reopening_id, assessment_id, record_id) VALUES (?,?,?,?,?)""",
            (str(uuid4()), project_id, reopening_id, successor_id, record_id),
        )
    return {
        "reopening": dict(
            connection.execute(
                "SELECT * FROM assessment_reopenings WHERE id=?", (reopening_id,)
            ).fetchone()
        ),
        "successor_assessment_id": successor_id,
        "revalidation_items": revalidation_items(connection, successor_id),
    }


def revalidate(
    connection: sqlite3.Connection,
    project_id: str,
    assessment_id: str,
    record_id: str,
    actor_id: str,
    note: str,
) -> dict[str, Any]:
    if not note.strip():
        raise ValueError("A revalidation note is required")
    item = connection.execute(
        """SELECT * FROM revalidation_items
           WHERE project_id=? AND assessment_id=? AND record_id=?""",
        (project_id, assessment_id, record_id),
    ).fetchone()
    if item is None:
        raise LookupError("Revalidation item not found")
    if item["revalidated_by"] is not None:
        raise ValueError("Record is already revalidated")
    connection.execute(
        """UPDATE revalidation_items SET revalidated_by=?, revalidated_at=?, note=?
           WHERE id=?""",
        (actor_id, _now(), note.strip(), item["id"]),
    )
    return dict(
        connection.execute("SELECT * FROM revalidation_items WHERE id=?", (item["id"],)).fetchone()
    )
