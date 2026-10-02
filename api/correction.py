"""Explicit presentation-only correction of the current issued HIPAA package."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from api.close import fieldwork_ready
from api.generation import _snapshot, render_package
from api.package_review import _content_hash, _package
from api.storage import FileStorage

PRESENTATION_ONLY = "presentation_only"
CORRECTION_TARGET = "presentation_correction"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def current_issuance(connection: sqlite3.Connection, project_id: str) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM current_issuances WHERE project_id=?", (project_id,)
        ).fetchone(),
    )


def correction_for(
    connection: sqlite3.Connection, project_id: str, package_id: str
) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM package_corrections WHERE project_id=? AND result_package_id=?",
            (project_id, package_id),
        ).fetchone(),
    )


def issuance_blockers(
    connection: sqlite3.Connection, project_id: str, package_id: str
) -> list[str]:
    """Only the first issue, or a correction of the current issue, may be issued."""
    current = current_issuance(connection, project_id)
    if current is None or current["package_id"] == package_id:
        return []
    correction = correction_for(connection, project_id, package_id)
    if correction is None:
        return [
            "A current issued package already exists; issue a presentation-only "
            "correction of it instead"
        ]
    if correction["prior_issuance_id"] != current["id"]:
        return ["The corrected package's prior issue is no longer the current issue"]
    return []


def create_correction(
    connection: sqlite3.Connection,
    storage: FileStorage,
    root: Path,
    project_id: str,
    prior_package_id: str,
    classification: str,
    unchanged_source_attested: bool,
    reason: str,
    actor_id: str,
    staging_root: Path | None = None,
) -> dict[str, Any]:
    if classification != PRESENTATION_ONLY:
        raise ValueError("Correction must be explicitly classified as presentation_only")
    if unchanged_source_attested is not True:
        raise ValueError("Unchanged-source attestation is required")
    if not reason.strip():
        raise ValueError("A correction reason is required")
    prior = _package(connection, project_id, prior_package_id)
    current = current_issuance(connection, project_id)
    if current is None or current["package_id"] != prior["id"]:
        raise ValueError("Only the current issued package can be corrected")
    stored = connection.execute(
        "SELECT * FROM source_snapshots WHERE id=? AND project_id=?",
        (prior["source_snapshot_id"], project_id),
    ).fetchone()
    assessment = connection.execute(
        """SELECT assessments.*, assessment_revisions.revision_number
           FROM assessments JOIN assessment_revisions
             ON assessment_revisions.assessment_id=assessments.id
            AND assessment_revisions.project_id=assessments.project_id
           WHERE assessments.id=? AND assessments.project_id=?""",
        (prior["assessment_id"], project_id),
    ).fetchone()
    if stored is None or assessment is None:
        raise ValueError("Prior package source binding is invalid")
    decision = fieldwork_ready(connection, project_id, prior["assessment_id"])
    if decision.get("status") != "Ready":
        raise ValueError(
            "Assessment is no longer ready; a presentation-only correction is not allowed"
        )
    source = json.loads(stored["source_json"])
    live, _, _ = _snapshot(connection, project_id, prior["assessment_id"], assessment)
    if _content_hash(live) != _content_hash(source):
        # Anything beyond presentation needs the substantive path, not this one.
        raise ValueError(
            "Assessment source changed since issue; a presentation-only correction is not allowed"
        )
    package = render_package(
        connection,
        storage,
        root,
        project_id,
        prior["assessment_id"],
        source,
        stored["sha256"],
        CORRECTION_TARGET,
        staging_root,
    )
    correction_id = str(uuid4())
    connection.execute(
        """INSERT INTO package_corrections(
          id, project_id, assessment_id, classification, unchanged_source_attested, reason,
          prior_package_id, prior_issuance_id, result_package_id, source_snapshot_id,
          actor_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            correction_id,
            project_id,
            prior["assessment_id"],
            PRESENTATION_ONLY,
            1,
            reason.strip(),
            prior["id"],
            current["id"],
            package["id"],
            prior["source_snapshot_id"],
            actor_id,
            _now(),
        ),
    )
    return {"correction": correction_summary(connection, correction_id), "package": package}


def correction_summary(connection: sqlite3.Connection, correction_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM package_corrections WHERE id=?", (correction_id,)
    ).fetchone()
    return dict(row)


def record_supersession(
    connection: sqlite3.Connection, project_id: str, package_id: str, actor_id: str
) -> None:
    """Link a correction's issue to the prior issue in the issuing transaction."""
    correction = correction_for(connection, project_id, package_id)
    if correction is None:
        return
    connection.execute(
        "INSERT INTO issuance_supersessions VALUES (?,?,?,?,?,?,?,?)",
        (
            str(uuid4()),
            project_id,
            correction["id"],
            correction["prior_issuance_id"],
            correction["prior_package_id"],
            package_id,
            actor_id,
            _now(),
        ),
    )


def package_issuance(
    connection: sqlite3.Connection, project_id: str, package_id: str
) -> dict[str, Any]:
    issued = connection.execute(
        "SELECT id, issued_at FROM issuance_snapshots WHERE project_id=? AND package_id=?",
        (project_id, package_id),
    ).fetchone()
    superseded = connection.execute(
        """SELECT s.result_package_id, r.issued_at FROM issuance_supersessions s
           JOIN issuance_snapshots r
             ON r.package_id=s.result_package_id AND r.project_id=s.project_id
           WHERE s.project_id=? AND s.prior_package_id=?""",
        (project_id, package_id),
    ).fetchone()
    correction = correction_for(connection, project_id, package_id)
    return {
        "issuance_status": (
            None if issued is None else ("Superseded" if superseded else "Current")
        ),
        "issued_snapshot_id": issued["id"] if issued else None,
        "issued_at": issued["issued_at"] if issued else None,
        "superseded_by_package_id": superseded["result_package_id"] if superseded else None,
        "superseded_at": superseded["issued_at"] if superseded else None,
        "correction": dict(correction) if correction else None,
    }
