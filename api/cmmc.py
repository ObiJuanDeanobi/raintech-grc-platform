"""CMMC Level 2 official scoring and requirement-level findings (GitHub issue #105).

Scoring reads only derived requirement status and the point values declared
from 32 CFR 170.24. A derived Not Met requirement owns one project-level
finding; its POA&M items are the corrective actions linked to that finding.
Pending produces follow-up work only.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

Derive = Callable[[Any, str, str], str]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def requirement_rows(connection: Any, framework_version_id: str) -> list[Any]:
    return list(
        connection.execute(
            """SELECT record_id, citation, title FROM framework_records
               WHERE framework_version_id = ? AND parent_id IS NULL ORDER BY sort_order""",
            (framework_version_id,),
        )
    )


def _objectives(connection: Any, assessment_id: str, requirement_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT r.record_id, r.citation, r.regulation_text,
                  COALESCE(d.status, '') AS status, COALESCE(n.note, '') AS note,
                  COALESCE(d.interview_observation, '') AS interview_observation
           FROM framework_records r
           JOIN assessments a ON a.framework_version_id = r.framework_version_id
           LEFT JOIN determinations d ON d.assessment_id = a.id AND d.record_id = r.record_id
           LEFT JOIN record_notes n ON n.assessment_id = a.id AND n.record_id = r.record_id
           WHERE a.id = ? AND r.parent_id = ? ORDER BY r.sort_order""",
        (assessment_id, requirement_id),
    )
    return [dict(row) for row in rows]


def _partial(connection: Any, assessment_id: str) -> dict[str, Any]:
    return {
        row["record_id"]: dict(row)
        for row in connection.execute(
            "SELECT record_id, implementation, rationale, updated_at "
            "FROM partial_implementations WHERE assessment_id = ?",
            (assessment_id,),
        )
    }


def _deduction(value: dict[str, Any], partial: dict[str, Any] | None) -> int | None:
    if value["rule"] == "fixed":
        return int(value["points"])
    if value["rule"] == "partial" and partial is not None:
        return int(value["points_by_implementation"][partial["implementation"]])
    return None


def score(
    connection: Any, assessment: Any, scoring: dict[str, Any], derive: Derive
) -> dict[str, Any]:
    partial = _partial(connection, assessment["id"])
    rules = scoring["conditional_poam"]
    deductions: list[dict[str, Any]] = []
    unscored: list[dict[str, str]] = []
    inputs_needed: list[str] = []
    follow_up: list[dict[str, str]] = []
    ssp_blocked = False
    for row in requirement_rows(connection, assessment["framework_version_id"]):
        requirement_id = row["record_id"]
        status = derive(connection, assessment["id"], requirement_id)
        value = scoring["requirements"][requirement_id]
        if status == "Pending":
            follow_up.extend(
                {
                    "record_id": o["record_id"],
                    "requirement_id": requirement_id,
                    "kind": "evidence_request",
                }
                for o in _objectives(connection, assessment["id"], requirement_id)
                if o["status"] == "Pending"
            )
        if status != "Not Met":
            if status != "Met":
                unscored.append({"record_id": requirement_id, "status": status or "Blank"})
            continue
        if value["rule"] == "ssp_required":
            ssp_blocked = True
        points = _deduction(value, partial.get(requirement_id))
        if value["rule"] == "partial" and points is None:
            inputs_needed.append(requirement_id)
        exception = rules["exceptions"].get(requirement_id)
        poam_allowed = requirement_id not in rules["excluded"] and (
            (points is not None and points <= rules["maximum_points"])
            or (
                exception is not None
                and partial.get(requirement_id, {}).get("implementation")
                == exception["implementation"]
            )
        )
        deductions.append(
            {
                "record_id": requirement_id,
                "citation": row["citation"],
                "title": row["title"],
                "points": points,
                "rule": value["rule"],
                "source": value["source"],
                "conditional_poam_allowed": poam_allowed,
            }
        )
    maximum = int(scoring["maximum_score"])
    total = maximum - sum(d["points"] or 0 for d in deductions)
    complete = not unscored and not inputs_needed and not ssp_blocked
    blockers = []
    if unscored:
        blockers.append(f"{len(unscored)} requirement(s) are not yet Met or Not Met.")
    if inputs_needed:
        blockers.append(
            "Record partial or no implementation for: " + ", ".join(inputs_needed) + "."
        )
    if ssp_blocked:
        blockers.append(scoring["requirements"]["CA.L2-3.12.4"]["note"])
    ratio = total / maximum
    return {
        "scoring_id": scoring["id"],
        "authority": scoring["authority"],
        "maximum_score": maximum,
        "minimum_score": scoring["minimum_score"],
        "score": total,
        "complete": complete,
        "blockers": blockers,
        "deductions": deductions,
        "unscored": unscored,
        "partial_inputs_needed": inputs_needed,
        "partial_implementations": partial,
        "follow_up": follow_up,
        "conditional": {
            "source": rules["source"],
            "score_ratio": round(ratio, 4),
            "eligible": complete
            and ratio >= rules["minimum_score_ratio"]
            and all(d["conditional_poam_allowed"] for d in deductions),
        },
    }


def _event(
    connection: Any,
    project_id: str,
    finding_id: str,
    assessment_id: str,
    event: str,
    failed: list[str],
) -> None:
    connection.execute(
        """INSERT INTO requirement_finding_events(
               id, project_id, finding_id, assessment_id, event, failed_objectives_json, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid4()), project_id, finding_id, assessment_id, event, json.dumps(failed), _now()),
    )


def sync_requirement_finding(
    connection: Any, project_id: str, assessment: Any, requirement_id: str, derive: Derive
) -> None:
    """Keep one finding per Not Met requirement; append history on every change.

    Idempotent: a retry or restart with unchanged state writes nothing.
    """
    status = derive(connection, assessment["id"], requirement_id)
    failed = [
        o["record_id"]
        for o in _objectives(connection, assessment["id"], requirement_id)
        if o["status"] == "Not Met"
    ]
    link = connection.execute(
        "SELECT finding_id FROM requirement_findings WHERE project_id = ? AND record_id = ?",
        (project_id, requirement_id),
    ).fetchone()
    if link is None:
        if status != "Not Met":
            return
        requirement = connection.execute(
            "SELECT citation, title FROM framework_records "
            "WHERE framework_version_id = ? AND record_id = ?",
            (assessment["framework_version_id"], requirement_id),
        ).fetchone()
        finding_id, created = str(uuid4()), _now()
        connection.execute(
            """INSERT INTO findings(id, project_id, title, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                finding_id,
                project_id,
                f"Not Met: {requirement['citation']} {requirement['title']}",
                "Requirement-level CMMC finding. Failed objectives are listed "
                "with their evidence and notes.",
                created,
                created,
            ),
        )
        connection.execute(
            """INSERT INTO requirement_findings(
                   project_id, record_id, finding_id, framework_version_id, created_at
               ) VALUES (?, ?, ?, ?, ?)""",
            (project_id, requirement_id, finding_id, assessment["framework_version_id"], created),
        )
        _event(connection, project_id, finding_id, assessment["id"], "opened", failed)
        return
    finding_id = link["finding_id"]
    last = connection.execute(
        """SELECT event, failed_objectives_json FROM requirement_finding_events
           WHERE finding_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1""",
        (finding_id,),
    ).fetchone()
    if status == "Not Met":
        if (
            last["event"] == "requirement_cleared"
            or json.loads(last["failed_objectives_json"]) != failed
        ):
            _event(
                connection, project_id, finding_id, assessment["id"], "objectives_changed", failed
            )
    elif last["event"] != "requirement_cleared":
        _event(connection, project_id, finding_id, assessment["id"], "requirement_cleared", failed)


def requirement_finding(
    connection: Any, project_id: str, assessment: Any, requirement_id: str, derive: Derive
) -> dict[str, Any] | None:
    link = connection.execute(
        "SELECT finding_id FROM requirement_findings WHERE project_id = ? AND record_id = ?",
        (project_id, requirement_id),
    ).fetchone()
    if link is None:
        return None
    finding = dict(
        connection.execute("SELECT * FROM findings WHERE id = ?", (link["finding_id"],)).fetchone()
    )
    objectives = []
    for objective in _objectives(connection, assessment["id"], requirement_id):
        if objective["status"] != "Not Met":
            continue
        objective["evidence"] = [
            dict(row)
            for row in connection.execute(
                """SELECT a.name, m.rationale FROM evidence_mappings m
                   JOIN evidence_artifacts a ON a.id = m.artifact_id
                   WHERE m.assessment_id = ? AND m.record_id = ?
                     AND m.target_type = 'assessment_record'""",
                (assessment["id"], objective["record_id"]),
            )
        ]
        objectives.append(objective)
    return {
        "finding": finding,
        "requirement_id": requirement_id,
        "requirement_status": derive(connection, assessment["id"], requirement_id),
        "failed_objectives": objectives,
        "poam_items": [
            dict(row)
            for row in connection.execute(
                """SELECT id, title, description, status, validation_state, created_at
                   FROM corrective_actions WHERE finding_id = ? AND project_id = ?
                   ORDER BY created_at""",
                (link["finding_id"], project_id),
            )
        ],
        "history": [
            {**dict(row), "failed_objectives": json.loads(row["failed_objectives_json"])}
            for row in connection.execute(
                """SELECT event, assessment_id, failed_objectives_json, created_at
                   FROM requirement_finding_events WHERE finding_id = ?
                   ORDER BY created_at, rowid""",
                (link["finding_id"],),
            )
        ],
    }


def add_poam_item(
    connection: Any, project_id: str, finding_id: str, title: str, description: str
) -> str:
    action_id, created = str(uuid4()), _now()
    connection.execute(
        """INSERT INTO corrective_actions(
               id, project_id, finding_id, title, description, created_at, updated_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (action_id, project_id, finding_id, title, description, created, created),
    )
    return action_id
