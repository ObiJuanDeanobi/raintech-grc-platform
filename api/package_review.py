"""Exact generated-package review and sign-off lifecycle."""

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from api.generation import TEMPLATES, _snapshot

STATES = ("Complete candidate", "In Review", "Reviewed", "Ready to issue")
TRANSITIONS = {STATES[0]: STATES[1], STATES[1]: STATES[2], STATES[2]: STATES[3]}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _content_hash(source: dict[str, Any]) -> str:
    value = {
        key: item for key, item in source.items() if key not in {"snapshot_id", "source_sha256"}
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()


def _package(connection: sqlite3.Connection, project_id: str, package_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM generated_packages WHERE id=? AND project_id=?", (package_id, project_id)
    ).fetchone()
    if row is None:
        raise LookupError("Package not found")
    return cast(sqlite3.Row, row)


def _binding(
    connection: sqlite3.Connection,
    package: sqlite3.Row,
    root: Path,
    storage_root: Path,
) -> dict[str, Any]:
    manifest = json.loads(package["manifest_json"])
    component_rows = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM generated_components WHERE package_id=? AND project_id=?",
            (package["id"], package["project_id"]),
        )
    ]
    component_hashes = {row["kind"]: row["sha256"] for row in component_rows}
    component_ids = {row["kind"]: row["id"] for row in component_rows}
    template_hashes = {
        kind: sha256((root / "docs/templates/hipaa/v2" / filename).read_bytes()).hexdigest()
        for kind, filename in TEMPLATES
    }
    blockers: list[str] = []
    drift: list[str] = []
    if package["state"] != "promoted":
        blockers.append("Only promoted complete candidates can be reviewed")
    expected_kinds = {kind for kind, _ in TEMPLATES}
    manifest_hashes = {
        item.get("kind"): item.get("sha256") for item in manifest.get("components", [])
    }
    if set(component_hashes) != expected_kinds or component_hashes != manifest_hashes:
        blockers.append("Package component binding is incomplete")
    resolved_storage = storage_root.resolve()
    for row in component_rows:
        path = (storage_root / row["relative_path"]).resolve()
        if resolved_storage not in path.parents or not path.is_file():
            blockers.append(f"Package component is unavailable: {row['kind']}")
        elif sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            blockers.append(f"Package component hash mismatch: {row['kind']}")
    source = connection.execute(
        "SELECT source_json, sha256 FROM source_snapshots WHERE id=? AND project_id=?",
        (package["source_snapshot_id"], package["project_id"]),
    ).fetchone()
    if source is None or source["sha256"] != manifest.get("source_snapshot_sha256"):
        blockers.append("Package source binding is invalid")
        stored_source: dict[str, Any] = {}
    else:
        stored_source = json.loads(source["source_json"])
    if template_hashes != manifest.get("template_hashes", {}):
        drift.append("Approved template bytes changed")
    attempt = connection.execute(
        """SELECT id, target, state FROM generation_attempts
           WHERE id=? AND project_id=? AND assessment_id=?""",
        (package["generation_attempt_id"], package["project_id"], package["assessment_id"]),
    ).fetchone()
    if attempt is None or attempt["state"] != "promoted":
        blockers.append("Package close-decision binding is invalid")
    close_decision = {
        "generation_attempt_id": attempt["id"] if attempt else "",
        "target": attempt["target"] if attempt else "",
        "decision": stored_source.get("readiness", {}),
    }
    assessment = connection.execute(
        """SELECT assessments.*, assessment_revisions.revision_number
           FROM assessments JOIN assessment_revisions
             ON assessment_revisions.assessment_id=assessments.id
            AND assessment_revisions.project_id=assessments.project_id
           WHERE assessments.id=? AND assessments.project_id=?""",
        (package["assessment_id"], package["project_id"]),
    ).fetchone()
    if assessment is None:
        blockers.append("Assessment is not in this project")
    elif stored_source:
        try:
            current_source, _, _ = _snapshot(
                connection, package["project_id"], package["assessment_id"], assessment
            )
            if _content_hash(current_source) != _content_hash(stored_source):
                drift.append("Assessment source changed after generation")
        except ValueError:
            drift.append("Assessment is no longer ready for generation")
    return {
        "package_sha256": package["sha256"],
        "source_snapshot_id": package["source_snapshot_id"],
        "source_snapshot_sha256": source["sha256"] if source else "",
        "template_version": package["template_version"],
        "component_ids": component_ids,
        "component_hashes": component_hashes,
        "template_hashes": template_hashes,
        "close_decision": close_decision,
        "drift": drift,
        "blockers": blockers,
    }


def get_review(
    connection: sqlite3.Connection,
    project_id: str,
    package_id: str,
    root: Path,
    storage_root: Path,
) -> dict[str, Any]:
    package = _package(connection, project_id, package_id)
    events = [
        dict(row)
        for row in connection.execute(
            """SELECT * FROM package_review_events
               WHERE package_id=? AND project_id=? ORDER BY sequence""",
            (package_id, project_id),
        )
    ]
    binding = _binding(connection, package, root, storage_root)
    latest = events[-1] if events else {}
    return {
        "package_id": package_id,
        "project_id": project_id,
        "state": latest.get("next_state", STATES[0]),
        "events": events,
        "reviewer_name": latest.get("reviewer_name", ""),
        "reviewer_role": latest.get("reviewer_role", ""),
        "note": latest.get("note", ""),
        "binding": binding,
        "drift": binding["drift"],
        "blockers": binding["blockers"],
    }


def transition(
    connection: sqlite3.Connection,
    project_id: str,
    package_id: str,
    next_state: str,
    actor_id: str,
    reviewer_name: str,
    reviewer_role: str,
    note: str,
    approval: str,
    confirmations: dict[str, bool],
    root: Path,
    storage_root: Path,
) -> dict[str, Any]:
    package = _package(connection, project_id, package_id)
    last = connection.execute(
        """SELECT * FROM package_review_events
           WHERE package_id=? AND project_id=? ORDER BY sequence DESC LIMIT 1""",
        (package_id, project_id),
    ).fetchone()
    prior = last["next_state"] if last else STATES[0]
    if TRANSITIONS.get(prior) != next_state:
        raise ValueError(f"Invalid transition from {prior} to {next_state}")
    if not reviewer_name.strip() or not reviewer_role.strip() or not note.strip():
        raise ValueError("Reviewer name, role, and review note are required")
    binding = _binding(connection, package, root, storage_root)
    if binding["blockers"] or binding["drift"]:
        raise ValueError(
            "Package review is blocked: " + "; ".join(binding["blockers"] + binding["drift"])
        )
    required = set(binding["component_hashes"]) | {"__source"}
    if next_state in {"Reviewed", "Ready to issue"} and not all(
        confirmations.get(key) is True for key in required
    ):
        raise ValueError("Every component, source snapshot, and template must be confirmed")
    if next_state == "Ready to issue" and not approval.strip():
        raise ValueError("Sign-off approval is required")
    sequence = (last["sequence"] if last else 0) + 1
    connection.execute(
        """INSERT INTO package_review_events(
           id, project_id, assessment_id, package_id, sequence, prior_state,
           next_state, actor_id, reviewer_name, reviewer_role, note, approval,
           confirmations_json, package_sha256, source_snapshot_id,
           source_snapshot_sha256, template_version, component_ids_json,
           component_hashes_json, template_hashes_json, close_decision_json, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(uuid4()),
            project_id,
            package["assessment_id"],
            package_id,
            sequence,
            prior,
            next_state,
            actor_id,
            reviewer_name.strip(),
            reviewer_role.strip(),
            note.strip(),
            approval.strip(),
            json.dumps(confirmations, sort_keys=True),
            binding["package_sha256"],
            binding["source_snapshot_id"],
            binding["source_snapshot_sha256"],
            binding["template_version"],
            json.dumps(binding["component_ids"], sort_keys=True),
            json.dumps(binding["component_hashes"], sort_keys=True),
            json.dumps(binding["template_hashes"], sort_keys=True),
            json.dumps(binding["close_decision"], sort_keys=True),
            _now(),
        ),
    )
    return get_review(connection, project_id, package_id, root, storage_root)
