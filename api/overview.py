"""Read-only Overview dashboard: where an engagement stands, as counts (#144).

Everything here is derived on read from existing records. Nothing is stored and
there is no schema change. The page shows grouped counts that open a filtered
list, never one line per blocker.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from api import cmmc
from api.close import _approved_profile, fieldwork_ready
from api.database import active_assessment_by_id, active_assessment_for_project

_STEP_LABELS = ("Scope", "Assess", "Remediate", "Deliver")
_BLANK = "Blank"


def _count(number: int, noun: str) -> str:
    """'1 item', '2 items': counts read right in the step rail."""
    return f"{number} {noun if number == 1 else noun + 's'}"


def _poam_states(connection: Any, project_id: str) -> dict[str, str]:
    """Per requirement: open, draft or closed. Withdrawn items count as none."""
    rank = {"closed": 1, "draft": 2, "open": 3}
    states: dict[str, str] = {}
    for row in connection.execute(
        """SELECT f.record_id, a.status FROM requirement_findings f
           JOIN corrective_actions a
             ON a.finding_id = f.finding_id AND a.project_id = f.project_id
           WHERE f.project_id = ? AND a.status != 'Withdrawn'""",
        (project_id,),
    ):
        state = {"Draft": "draft", "Closed": "closed"}.get(row["status"], "open")
        if rank[state] > rank.get(states.get(row["record_id"], ""), 0):
            states[row["record_id"]] = state
    return states


def _resume(connection: Any, assessment: Any, records: dict[str, Any]) -> dict[str, Any] | None:
    """The requirement (or standard) whose determination changed most recently.

    Order: newest ``updated_at`` first; a tie (two saves in the same instant) goes to
    the record later in the framework's own ``sort_order``, so the answer never
    depends on insertion order.
    """
    row = connection.execute(
        """SELECT d.record_id, d.updated_at FROM determinations d
           JOIN framework_records r
             ON r.framework_version_id = ? AND r.record_id = d.record_id
           WHERE d.assessment_id = ?
           ORDER BY d.updated_at DESC, r.sort_order DESC LIMIT 1""",
        (assessment["framework_version_id"], assessment["id"]),
    ).fetchone()
    record = records.get(row["record_id"]) if row else None
    if record is None:
        return None
    if record["parent_id"]:
        record = records[record["parent_id"]]
    return {
        "record_id": record["record_id"],
        "citation": record["citation"],
        "title": record["title"],
        "updated_at": row["updated_at"],
    }


def overview(
    connection: Any,
    project_id: str,
    assessment_id: str | None = None,
    storage_root: Path | None = None,
) -> dict[str, Any]:
    # Imported here: api.main imports this module to register the route.
    from api.main import _record_states, _walkthrough_records

    project = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if assessment_id is None:
        assessment = active_assessment_for_project(connection, project_id)
    else:
        assessment = active_assessment_by_id(connection, assessment_id)
        if assessment is not None and assessment["project_id"] != project_id:
            assessment = None
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found for project")
    framework = connection.execute(
        "SELECT * FROM framework_versions WHERE id = ?", (assessment["framework_version_id"],)
    ).fetchone()
    declarations = json.loads(framework["declarations_json"])
    requirement_centred = declarations.get("presentation_mode") == "requirement_with_objectives"

    rows = _walkthrough_records(connection, assessment["framework_version_id"])
    records = {row["record_id"]: row for row in rows}
    states = _record_states(connection, assessment, rows, declarations["rollup_rule"])
    status_set = [str(status) for status in declarations.get("status_set", []) if status]
    deciding = [row for row in rows if row["carries_determination"]]
    decided_statuses = {"Met", "Not Met", "N/A"}
    decided = sum(1 for row in deciding if states[row["record_id"]]["status"] in decided_statuses)

    close = fieldwork_ready(connection, project_id, assessment["id"], storage_root)
    left_count = len(close["blockers"])
    poam_states = _poam_states(connection, project_id)
    open_actions = connection.execute(
        """SELECT COUNT(*) AS count FROM corrective_actions
           WHERE project_id = ? AND status NOT IN ('Closed', 'Withdrawn')""",
        (project_id,),
    ).fetchone()["count"]

    result: dict[str, Any] = {
        "variant": "cmmc" if requirement_centred else "hipaa",
        "project_id": project_id,
        "assessment_id": assessment["id"],
        "framework_id": framework["id"],
        "families": [],
        "not_met": [],
        "not_met_without_poam": None,
        "status_counts": None,
        "resume": _resume(connection, assessment, records),
        "left_before_issue": {
            "ready": close["ready"],
            "count": left_count,
            "groups": close["groups"],
        },
    }

    if requirement_centred:
        requirements = [row for row in rows if not row["parent_id"]]
        families: dict[str, dict[str, Any]] = {}

        def family_for(name: str) -> dict[str, Any]:
            return families.setdefault(name, {"name": name, "decided": 0, "total": 0, "not_met": 0})

        for row in deciding:
            parent = records[row["parent_id"]] if row["parent_id"] else row
            family = family_for(parent["work_area"])
            family["total"] += 1
            if states[row["record_id"]]["status"] in decided_statuses:
                family["decided"] += 1
        not_met_ids = [
            row["record_id"]
            for row in requirements
            if states[row["record_id"]]["status"] == "Not Met"
        ]
        for record_id in not_met_ids:
            family_for(records[record_id]["work_area"])["not_met"] += 1
        result["families"] = list(families.values())
        result["not_met"] = [
            {
                "record_id": record_id,
                "citation": records[record_id]["citation"],
                "title": records[record_id]["title"],
                "poam_state": poam_states.get(record_id, "none"),
            }
            for record_id in not_met_ids
        ]
        unplanned = cmmc.not_met_without_poam(connection, project_id, not_met_ids)
        result["not_met_without_poam"] = unplanned
        remediate = (
            f"{_count(open_actions, 'open POA&M item')} · "
            f"{_count(unplanned['count'], 'gap')} without a plan"
        )
        assess = f"{decided} of {_count(len(deciding), 'objective')} decided"
    else:
        counts: dict[str, dict[str, int]] = {}
        for row in deciding:
            per_rule = counts.setdefault(
                row["work_area"], {status: 0 for status in [*status_set, _BLANK]}
            )
            status = states[row["record_id"]]["status"] or _BLANK
            per_rule[status] = per_rule.get(status, 0) + 1
        result["status_counts"] = [
            {"rule": rule, "total": sum(per_rule.values()), "counts": per_rule}
            for rule, per_rule in counts.items()
        ]
        remediate = _count(open_actions, "open corrective action")
        assess = f"{decided} of {_count(len(deciding), 'record')} decided"

    approved = _approved_profile(connection, project) is not None
    figures = (
        "Profile approved" if approved else "Profile not approved",
        assess,
        remediate,
        "Ready to issue" if close["ready"] else f"{_count(left_count, 'item')} left before issue",
    )
    targets = ("profile", "assessments", "assessments", "reports")
    result["steps"] = [
        {"label": label, "figure": figure, "target": target}
        for label, figure, target in zip(_STEP_LABELS, figures, targets, strict=True)
    ]
    return result
