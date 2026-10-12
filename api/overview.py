"""Read-only Overview dashboard: where an engagement stands, as counts (#144).

Everything here is derived on read from existing records. Nothing is stored and
there is no schema change. The page shows progress and the next piece of work
(ADR 0022); the reasons something cannot be finalized appear only in the
finalize dialog. Each progress figure may carry a ``group`` that opens the
matching filtered list.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from api import cmmc
from api.correction import current_issuance
from api.database import active_assessment_by_id, active_assessment_for_project

_STEP_LABELS = ("Scope", "Assess", "Remediate", "Deliver")
_BLANK = "Blank"
# What the list filter says while someone works through a progress figure. The keys
# match the close check's group keys, so one opened list keeps the same name everywhere.
_FILTER_LABELS = {
    "undecided": "Not decided yet",
    "gaps_no_plan": "NOT MET without a POA&M",
    "gaps_no_action": "Not Met without a corrective action",
    "poam_open": "Open POA&M items",
    "met_no_evidence": "Met, evidence still needed",
    "recheck": "Records to recheck",
    "na_reason": "N/A answers that need a reason",
}


def _count(number: int, noun: str) -> str:
    """'1 item', '2 items': counts read right in the step rail."""
    return f"{number} {noun if number == 1 else noun + 's'}"


def _profile_progress(connection: Any, project: Any) -> str:
    """'Profile: 7 facts recorded · 2 to follow up'. Never says approved, never "N of M".

    The neutral Profile form declares no required fields, so there is no honest
    denominator; saying "N of M" would imply a completeness the form cannot measure.
    A fact is recorded when it has a value other than Unknown / To Determine (those
    are counted as follow-up). The auto-filled project name does not count. The newest
    version is used, because that is the one being worked on.
    """
    from api.main import _profile_unknowns

    row = connection.execute(
        "SELECT id FROM profile_versions WHERE project_id = ? "
        "ORDER BY version_number DESC LIMIT 1",
        (project["id"],),
    ).fetchone()
    if row is None:
        return "Profile: no facts recorded yet"
    version_id = row["id"]
    recorded = int(
        connection.execute(
            """SELECT COUNT(*) FROM profile_field_values v
               LEFT JOIN profile_items i ON i.id = v.profile_item_id
               WHERE v.profile_version_id = ?
                 AND (i.id IS NULL OR i.item_type != 'unknown_follow_up')
                 AND v.source != 'Project creation'
                 AND trim(v.value) != ''
                 AND lower(trim(v.value))
                     NOT IN ('unknown', 'to determine', 'unknown / to determine')""",
            (version_id,),
        ).fetchone()[0]
    )
    unknowns = _profile_unknowns(connection, version_id)
    if recorded == 0 and unknowns == 0:
        return "Profile: no facts recorded yet"
    text = f"Profile: {recorded} {'fact' if recorded == 1 else 'facts'} recorded"
    return f"{text} · {unknowns} to follow up" if unknowns else text


def _deliver_figure(connection: Any, project_id: str, assessment_id: str) -> str:
    """'Draft available', 'Final v2 · 12 Oct 2026', or 'Final v2 · new version in progress'."""
    current = current_issuance(connection, project_id)
    if current is None:
        return "Draft available"
    version = max(
        int(
            connection.execute(
                "SELECT COUNT(*) FROM issuance_snapshots WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
        ),
        1,
    )
    if current["assessment_id"] != assessment_id:
        # Reopened: the final version stands until the new one is finalized.
        return f"Final v{version} · new version in progress"
    issued = datetime.fromisoformat(str(current["issued_at"]))
    return f"Final v{version} · {issued.day} {issued.strftime('%b %Y')}"


def _part(text: str, group: dict[str, Any] | None) -> dict[str, Any]:
    """One clickable figure. ``group`` opens the matching filtered list when set."""
    return {"text": text, "group": group}


def _group(key: str, record_ids: list[str], count: int | None = None) -> dict[str, Any]:
    """The filtered list behind a figure, in the shape the app's list filter takes."""
    return {
        "key": key,
        "label": _FILTER_LABELS[key],
        "count": len(record_ids) if count is None else count,
        "record_ids": record_ids,
        "target": "assessments",
    }


def _figure(
    text: str, key: str, record_ids: list[str], count: int | None = None
) -> dict[str, Any]:
    """A figure that opens its list, or plain text when there is nothing behind it."""
    return _part(text, _group(key, record_ids, count) if record_ids else None)


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

    poam_states = _poam_states(connection, project_id)
    open_actions = connection.execute(
        """SELECT COUNT(*) AS count FROM corrective_actions
           WHERE project_id = ? AND status NOT IN ('Closed', 'Withdrawn')""",
        (project_id,),
    ).fetchone()["count"]
    deciding_ids = [row["record_id"] for row in deciding]
    undecided_ids = [
        record_id
        for record_id in deciding_ids
        if states[record_id]["status"] not in decided_statuses
    ]
    awaiting_evidence_ids = (
        [
            record_id
            for record_id in deciding_ids
            if states[record_id]["status"] == "Met"
            and states[record_id]["verification"] == "evidence_pending"
        ]
        if declarations.get("met_without_evidence") == "evidence_pending"
        else []
    )
    recheck_ids = [
        row["record_id"]
        for row in connection.execute(
            """SELECT record_id FROM revalidation_items
               WHERE project_id = ? AND assessment_id = ? AND revalidated_by IS NULL
               ORDER BY record_id""",
            (project_id, assessment["id"]),
        )
    ]
    deciding_set = set(deciding_ids)
    na_reason_ids = [
        row["record_id"]
        for row in connection.execute(
            """SELECT record_id FROM determinations
               WHERE assessment_id = ? AND status = 'N/A' AND trim(na_rationale) = ''
               ORDER BY record_id""",
            (assessment["id"],),
        )
        if row["record_id"] in deciding_set
    ]

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
        "evidence_progress": None,
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
        gaps = unplanned["count"]
        open_ids = [
            record_id for record_id, state in poam_states.items() if state in ("draft", "open")
        ]
        remediate_parts = [
            _figure(
                f"{_count(gaps, 'gap')} need{'s' if gaps == 1 else ''} a POA&M",
                "gaps_no_plan",
                unplanned["requirement_ids"],
                gaps,
            ),
            _figure(
                f"{_count(open_actions, 'POA&M item')} open", "poam_open", open_ids, open_actions
            ),
        ]
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
        reconciled = {
            row["record_id"]
            for row in connection.execute(
                """SELECT record_id FROM not_met_reconciliations
                   WHERE project_id = ? AND assessment_id = ?
                     AND finding_id IS NOT NULL AND finding_id != ''
                     AND corrective_action_id IS NOT NULL AND corrective_action_id != ''""",
                (project_id, assessment["id"]),
            )
        }
        no_action_ids = [
            record_id
            for record_id in deciding_ids
            if states[record_id]["status"] == "Not Met" and record_id not in reconciled
        ]
        remediate_parts = []
        if no_action_ids:
            count = len(no_action_ids)
            remediate_parts.append(
                _figure(
                    f"{count} Not Met need{'s' if count == 1 else ''} a corrective action",
                    "gaps_no_action",
                    no_action_ids,
                )
            )
        remediate_parts.append(_part(f"{_count(open_actions, 'corrective action')} open", None))

    if awaiting_evidence_ids:
        result["evidence_progress"] = _figure(
            f"{len(awaiting_evidence_ids)} Met awaiting evidence",
            "met_no_evidence",
            awaiting_evidence_ids,
        )
    assess_parts = [_figure(f"{decided} of {len(deciding)} decided", "undecided", undecided_ids)]
    if na_reason_ids:
        count = len(na_reason_ids)
        assess_parts.append(
            _figure(
                f"{count} N/A {'answer needs' if count == 1 else 'answers need'} a reason",
                "na_reason",
                na_reason_ids,
            )
        )
    if recheck_ids:
        count = len(recheck_ids)
        assess_parts.append(
            _figure(
                f"{count} {'record' if count == 1 else 'records'} to recheck",
                "recheck",
                recheck_ids,
            )
        )

    scope_parts = [_part(_profile_progress(connection, project), None)]
    steps_parts = (
        scope_parts,
        assess_parts,
        remediate_parts,
        [_part(_deliver_figure(connection, project_id, assessment["id"]), None)],
    )
    targets = ("profile", "assessments", "assessments", "reports")
    result["steps"] = [
        {
            "label": label,
            "figure": " · ".join(part["text"] for part in parts),
            "parts": parts,
            "target": target,
        }
        for label, parts, target in zip(_STEP_LABELS, steps_parts, targets, strict=True)
    ]
    return result
