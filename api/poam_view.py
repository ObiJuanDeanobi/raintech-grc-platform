"""Read-only POA&M list: every POA&M item (CMMC) or corrective action (HIPAA) of a project.

Derived on read from existing records; nothing is stored and there is no schema
change. One row per ``corrective_actions`` row, scoped by ``project_id``. CMMC
items are tied to a requirement through ``requirement_findings``; HIPAA
corrective actions through ``not_met_reconciliations``.

Owner and due date are not columns of ``corrective_actions``, so they are not
returned; ``missing_fields`` says so, and the page shows what exists.
"""

import json
from typing import Any

from fastapi import HTTPException

from api import cmmc
from api.database import active_assessment_by_id

# Plain names for the stored work statuses. Anything else is shown as stored.
STATUS_LABELS = {
    "Draft": "Draft",
    "Open": "Open",
    "In Progress": "In progress",
    "Waiting": "Waiting",
    "Ready for Validation": "Ready for validation",
    "Closed": "Closed",
    "Withdrawn": "Withdrawn",
}
# Where a row sits in the default order: work that needs a decision first.
_GROUP_ORDER = {
    "Ready for Validation": 0,
    "Open": 1,
    "In Progress": 1,
    "Waiting": 1,
    "Draft": 2,
    "Closed": 3,
    "Withdrawn": 4,
}
UNLINKED = "Not linked to a record"
# Workflow order, used when the list is sorted by status.
_WORKFLOW = list(STATUS_LABELS)
# Fields a consultant would expect on a POA&M that the stored model does not have.
MISSING_FIELDS = ["owner", "due_date"]
_TERMINAL = cmmc.TERMINAL_POAM_STATUSES


def _group(status: str) -> str:
    """open, draft, closed or withdrawn. Closed and Withdrawn are both not open."""
    if status == "Draft":
        return "draft"
    if status in ("Closed", "Withdrawn"):
        return status.lower()
    return "open"


def _eligibility(line: dict[str, Any] | None, scored: bool) -> dict[str, Any]:
    """32 CFR 170.21 POA&M eligibility, from the score's own ``_poam_eligibility`` result."""
    if not scored:
        return {"state": "not_applicable", "reason": ""}
    if line is None:
        return {
            "state": "not_applicable",
            "reason": "The requirement is currently verified Met, so it is not a gap.",
        }
    return {
        "state": "eligible" if line["conditional_poam_allowed"] else "not_eligible",
        "reason": line["poam_reason"],
    }


def poam_items(connection: Any, project_id: str, assessment_id: str) -> dict[str, Any]:
    # Imported here: api.main imports this module to register the route.
    from api.main import _derived_status, _record_states, _walkthrough_records

    assessment = active_assessment_by_id(connection, assessment_id)
    if assessment is None or assessment["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Assessment not found for project")
    framework = connection.execute(
        "SELECT * FROM framework_versions WHERE id = ?", (assessment["framework_version_id"],)
    ).fetchone()
    declarations = json.loads(framework["declarations_json"])
    is_cmmc = declarations.get("presentation_mode") == "requirement_with_objectives"
    scoring = declarations.get("scoring")

    rows = _walkthrough_records(connection, assessment["framework_version_id"])
    records = {row["record_id"]: row for row in rows}
    states = _record_states(connection, assessment, rows, declarations["rollup_rule"])
    lines: dict[str, dict[str, Any]] = {}
    if is_cmmc and scoring:
        score = cmmc.score(connection, assessment, scoring, _derived_status)
        lines = {line["record_id"]: line for line in score["deductions"]}

    # Every corrective action of the project is listed, linked to a record or not. A HIPAA
    # action is unlinked when its reconciliation was changed to "Not needed" or pointed at
    # another action; it is still open work, and the Overview and the issue checklist still
    # count it, so it must not vanish from this list. One row per action id; when several
    # reconciliations point at one action the most recently updated wins.
    if is_cmmc:
        links = connection.execute(
            """SELECT a.*, f.record_id FROM corrective_actions a
               LEFT JOIN requirement_findings f
                 ON f.finding_id = a.finding_id AND f.project_id = a.project_id
               WHERE a.project_id = ?""",
            (project_id,),
        ).fetchall()
    else:
        links = connection.execute(
            """SELECT a.*, r.record_id FROM corrective_actions a
               LEFT JOIN not_met_reconciliations r
                 ON r.corrective_action_id = a.id AND r.project_id = a.project_id
               WHERE a.project_id = ?
               ORDER BY r.updated_at""",
            (project_id,),
        ).fetchall()

    closures = {
        row["corrective_action_id"]: {"rationale": row["rationale"], "closed_at": row["closed_at"]}
        for row in connection.execute(
            """SELECT corrective_action_id, rationale, closed_at FROM poam_closures
               WHERE project_id = ?""",
            (project_id,),
        )
    }
    # HIPAA closes through a recorded validation; its notes are the closure rationale.
    for row in connection.execute(
        """SELECT corrective_action_id, notes, created_at FROM validation_events
           WHERE project_id = ? AND outcome = 'Validated' ORDER BY created_at, rowid""",
        (project_id,),
    ):
        closures[row["corrective_action_id"]] = {
            "rationale": row["notes"],
            "closed_at": row["created_at"],
        }

    items: dict[str, dict[str, Any]] = {}
    for link in links:
        record = records.get(link["record_id"]) if link["record_id"] else None
        status = link["status"]
        closure = closures.get(link["id"]) if status == "Closed" else None
        weight = lines.get(link["record_id"], {}).get("points")
        items[link["id"]] = {
            "id": link["id"],
            "record_id": link["record_id"],
            "linked": link["record_id"] is not None,
            "citation": record["citation"] if record else (link["record_id"] or UNLINKED),
            "requirement_title": record["title"] if record else "",
            "work_area": record["work_area"] if record else "",
            "sort_order": record["sort_order"] if record else 0,
            "requirement_status": states[link["record_id"]]["status"] if record else "",
            "title": link["title"],
            "description": link["description"],
            "status": status,
            "status_label": STATUS_LABELS.get(status, status),
            "group": _group(status),
            "status_rank": _WORKFLOW.index(status) if status in _WORKFLOW else len(_WORKFLOW),
            "validation_state": link["validation_state"],
            "weight": weight if is_cmmc else None,
            "eligibility": _eligibility(lines.get(link["record_id"]), is_cmmc and bool(scoring)),
            "closure_rationale": closure["rationale"] if closure else None,
            "closed_at": closure["closed_at"] if closure else None,
            "created_at": link["created_at"],
            "updated_at": link["updated_at"],
        }
    ordered = sorted(
        items.values(),
        key=lambda item: (_GROUP_ORDER.get(item["status"], 1), item["sort_order"], item["id"]),
    )

    counts = {"open": 0, "draft": 0, "closed": 0, "withdrawn": 0}
    for item in ordered:
        counts[item["group"]] += 1
    # "Open" is every non-terminal status, Draft included, as in the Overview's Remediate
    # figure; "draft" is the part of it still being written.
    counts["open"] += counts["draft"]
    counts["ready_for_validation"] = sum(
        1 for item in ordered if item["status"] == "Ready for Validation"
    )
    counts["total"] = len(ordered)

    deciding = [row for row in rows if row["carries_determination"]]
    if is_cmmc:
        not_met_ids = [
            row["record_id"]
            for row in rows
            if not row["parent_id"] and states[row["record_id"]]["status"] == "Not Met"
        ]
        unplanned = cmmc.not_met_without_poam(connection, project_id, not_met_ids)
        without_plan = {**unplanned, "not_needed_count": 0}
    else:
        not_met_ids = [
            row["record_id"] for row in deciding if states[row["record_id"]]["status"] == "Not Met"
        ]
        # How this differs from the finalize check (api/close.py, not_met_unreconciled): that
        # check passes a Not Met record once its reconciliation in THIS assessment names any
        # corrective action, even a Closed or Withdrawn one, and fails "Not needed". This
        # figure is about work in flight, so it counts a record as planned only while some
        # action linked to it, from any assessment of the project (an open action is open
        # whichever assessment recorded it), is neither Closed nor Withdrawn. "Not needed" is
        # a decision about the current determination, so it is read from this assessment only.
        planned = {
            item["record_id"]
            for item in items.values()
            if item["record_id"] and item["status"] not in _TERMINAL
        }
        not_needed = {
            row["record_id"]
            for row in connection.execute(
                """SELECT record_id FROM not_met_reconciliations
                   WHERE project_id = ? AND assessment_id = ? AND outcome = 'not_needed'""",
                (project_id, assessment_id),
            )
        }
        ids = [r for r in not_met_ids if r not in planned and r not in not_needed]
        without_plan = {
            "count": len(ids),
            "requirement_ids": ids,
            "not_needed_count": sum(1 for r in not_met_ids if r in not_needed and r not in planned),
        }

    work_areas = sorted(
        {item["work_area"] for item in ordered if item["work_area"]},
        key=lambda area: min(i["sort_order"] for i in ordered if i["work_area"] == area),
    )
    return {
        "variant": "cmmc" if is_cmmc else "hipaa",
        "project_id": project_id,
        "assessment_id": assessment_id,
        "framework_id": framework["id"],
        "item_label": "POA&M item" if is_cmmc else "corrective action",
        "scored": bool(is_cmmc and scoring),
        "items": ordered,
        "counts": counts,
        "work_areas": work_areas,
        # Records currently Not Met (CMMC: requirements), so the page can tell "none missing a
        # plan" from "nothing is Not Met".
        "not_met_count": len(not_met_ids),
        "not_met_without_plan": without_plan,
        "missing_fields": MISSING_FIELDS,
    }
