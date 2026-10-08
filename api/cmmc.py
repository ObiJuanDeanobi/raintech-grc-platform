"""CMMC Level 2 official scoring and requirement-level findings (GitHub issue #105).

Scoring reads only derived requirement status, objective verification (#141),
and the point values declared from 32 CFR 170.24, reconciled with the DoD
Assessment Methodology v1.2.1. A derived Not Met requirement owns one project-level
finding; its POA&M items are the corrective actions linked to that finding.
Pending produces follow-up work only.
"""

import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from fractions import Fraction
from typing import Any
from uuid import uuid4

from api import verification

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


MINUS = "−"
METHODOLOGY = (
    "NIST SP 800-171 DoD Assessment Methodology v1.2.1 (June 24, 2020), section 5 "
    "and Annex A; point values as published in 32 CFR 170.24(c)(2)(i)(B)"
)


def _objective_ids(connection: Any, framework_version_id: str) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    for row in connection.execute(
        """SELECT record_id, parent_id FROM framework_records
           WHERE framework_version_id = ? AND parent_id IS NOT NULL ORDER BY sort_order""",
        (framework_version_id,),
    ):
        children.setdefault(row["parent_id"], []).append(row["record_id"])
    return children


def _weight(value: dict[str, Any], partial: dict[str, Any] | None, state: str) -> int | None:
    """Points subtracted from 110 for a requirement that does not count as Met.

    DoD Assessment Methodology v1.2.1 section 5(b), p. 5: "For each security
    requirement not met, the associated value is subtracted from 110."

    Partial credit, section 5(e), p. 7, and Annex A, pp. 15 and 19 (the same
    values as 32 CFR 170.24(c)(2)(i)(B)(4)):
    - 3.5.3 MFA implemented only for remote and privileged users: 3; MFA not
      implemented for any users: 5.
    - 3.13.11 encryption employed but not FIPS-validated: 3; not employed: 5.
    Partial credit is applied only to a Not Met requirement whose implementation
    level was recorded in ``partial_implementations``. Any other state that does
    not count as Met deducts the full value, never less.

    3.12.4 (SSP) has no value: section 5(g)(i), p. 7; Annex A, p. 18 ("NA").
    """
    if value["rule"] == "fixed":
        return int(value["points"])
    if value["rule"] == "partial":
        levels = value["points_by_implementation"]
        if state == "not_met" and partial is not None:
            return int(levels[partial["implementation"]])
        return max(int(points) for points in levels.values())
    return None


def _poam_eligibility(
    requirement_id: str,
    points: int | None,
    partial: dict[str, Any] | None,
    rules: dict[str, Any],
) -> tuple[bool, str]:
    """Whether a requirement that is not verified Met could sit on a POA&M.

    32 CFR 170.21(a)(2)(ii) and (iii), read from the framework scoring data.
    """
    paragraphs = rules["paragraphs"]
    if requirement_id in rules["excluded"]:
        return False, f"May never be on a POA&M ({paragraphs['excluded']})."
    exception = rules["exceptions"].get(requirement_id)
    if (
        exception is not None
        and partial is not None
        and partial["implementation"] == exception["implementation"]
        and points == exception["points"]
    ):
        return True, f"{exception['note']} Named exception in {paragraphs['maximum_points']}."
    if points is not None and points <= rules["maximum_points"]:
        return True, f"{points}-point requirement ({paragraphs['maximum_points']})."
    return False, (
        f"{points}-point requirement; only 1-point requirements may be on a POA&M "
        f"({paragraphs['maximum_points']})."
    )


def _figure(maximum: int, lines: list[dict[str, Any]]) -> dict[str, Any]:
    """One score, its deduction lines and its literal arithmetic (110 minus each weight)."""
    deductions = [line for line in lines if line["points"] is not None]
    value = maximum - sum(int(line["points"]) for line in deductions)
    shown = f"{MINUS}{-value}" if value < 0 else str(value)
    terms = "".join(f" {MINUS} {line['points']}" for line in deductions)
    return {
        "value": value,
        "deductions": [
            {"record_id": line["record_id"], "points": line["points"], "state": line["state"]}
            for line in deductions
        ],
        "arithmetic": f"{maximum}{terms} = {shown}",
    }


def _conditional(
    scoring: dict[str, Any],
    verified: int,
    lines: list[dict[str, Any]],
    titles: dict[str, str],
    states: dict[str, str],
    complete: bool,
) -> dict[str, Any]:
    """32 CFR 170.21(a)(2) Conditional Level 2 checks, on the verified score only."""
    rules = scoring["conditional_poam"]
    paragraphs = rules["paragraphs"]
    maximum = int(scoring["maximum_score"])
    ratio = Fraction(str(rules["minimum_score_ratio"]))
    minimum = math.ceil(maximum * ratio)
    achieved = Fraction(verified, maximum)
    candidates = [
        {
            "record_id": line["record_id"],
            "title": line["title"],
            "state": line["state"],
            "points": line["points"],
            "allowed": line["conditional_poam_allowed"],
            "reason": line["poam_reason"],
        }
        for line in lines
        if line["record_id"] not in rules["excluded"]
    ]
    never = [
        {
            "record_id": requirement_id,
            "title": titles.get(requirement_id, ""),
            "state": states.get(requirement_id, "not_assessed"),
        }
        for requirement_id in rules["excluded"]
    ]
    checks = [
        {
            "key": "minimum_score",
            "source": paragraphs["minimum_score"],
            "passed": achieved >= ratio,
            "detail": (
                f"Verified score {verified} ÷ {maximum} = {float(achieved):.3f}; "
                f"at least {float(ratio)} is required, so at least {minimum} of {maximum}."
            ),
        },
        {
            "key": "maximum_points",
            "source": paragraphs["maximum_points"],
            "passed": all(item["allowed"] for item in candidates),
            "detail": (
                "Every requirement that is not verified Met must be POA&M-eligible: point "
                f"value {rules['maximum_points']}, or SC.L2-3.13.11 with encryption employed "
                "but not FIPS-validated."
            ),
            "items": candidates,
        },
        {
            "key": "excluded",
            "source": paragraphs["excluded"],
            "passed": all(item["state"] == "met" for item in never),
            "detail": "These may never be on a POA&M, so each must be verified Met.",
            "items": never,
        },
    ]
    return {
        "source": rules["source"],
        "score_ratio": round(float(achieved), 4),
        "minimum_score": minimum,
        "eligible": complete and all(check["passed"] for check in checks),
        "checks": checks,
    }


def score(
    connection: Any, assessment: Any, scoring: dict[str, Any], derive: Derive
) -> dict[str, Any]:
    """Verified and projected scores from the official model (GitHub issue #141).

    Verified counts as Met only requirements whose objectives are all verified
    Met (``api.verification``); it is the headline and the only figure that may
    be issued. Projected also counts evidence-pending Met as Met. Every other
    requirement deducts its weight in both, so neither is inflated by work not
    yet done.
    """
    partial = _partial(connection, assessment["id"])
    rules = scoring["conditional_poam"]
    bases = verification.met_bases(connection, assessment["id"])
    objectives = _objective_ids(connection, assessment["framework_version_id"])
    lines: list[dict[str, Any]] = []
    states: dict[str, str] = {}
    titles: dict[str, str] = {}
    unscored: list[dict[str, str]] = []
    inputs_needed: list[str] = []
    follow_up: list[dict[str, str]] = []
    evidence_pending: list[str] = []
    ssp_blocked = False
    for row in requirement_rows(connection, assessment["framework_version_id"]):
        requirement_id = row["record_id"]
        titles[requirement_id] = row["title"]
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
        verified = verification.state(status, objectives.get(requirement_id, []), bases)
        if status == "Met":
            state = "met" if verified == verification.VERIFIED else "evidence_pending"
        else:
            state = {"Not Met": "not_met", "Pending": "pending"}.get(status, "not_assessed")
            if status != "Not Met":
                unscored.append({"record_id": requirement_id, "status": status or "Blank"})
        states[requirement_id] = state
        if state == "met":
            continue
        if state == "evidence_pending":
            evidence_pending.append(requirement_id)
        if state == "not_met" and value["rule"] == "ssp_required":
            ssp_blocked = True
        if state == "not_met" and value["rule"] == "partial" and requirement_id not in partial:
            inputs_needed.append(requirement_id)
        points = _weight(value, partial.get(requirement_id), state)
        allowed, reason = _poam_eligibility(
            requirement_id, points, partial.get(requirement_id), rules
        )
        lines.append(
            {
                "record_id": requirement_id,
                "citation": row["citation"],
                "title": row["title"],
                "points": points,
                "state": state,
                "rule": value["rule"],
                "source": value["source"],
                "conditional_poam_allowed": allowed,
                "poam_reason": reason,
            }
        )
    maximum = int(scoring["maximum_score"])
    verified_figure = _figure(maximum, lines)
    projected_figure = _figure(
        maximum, [line for line in lines if line["state"] != "evidence_pending"]
    )
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
    unplanned = not_met_without_poam(
        connection,
        assessment["project_id"],
        [record_id for record_id, state in states.items() if state == "not_met"],
    )
    return {
        "scoring_id": scoring["id"],
        "authority": scoring["authority"],
        "methodology": METHODOLOGY,
        "maximum_score": maximum,
        "minimum_score": scoring["minimum_score"],
        # The headline is the verified score, the only figure that may be issued.
        "score": verified_figure["value"],
        "verified": verified_figure,
        "projected": projected_figure,
        "complete": complete,
        "blockers": blockers,
        "deductions": lines,
        "evidence_pending": evidence_pending,
        "unscored": unscored,
        "partial_inputs_needed": inputs_needed,
        "partial_implementations": partial,
        "follow_up": follow_up,
        "conditional": _conditional(
            scoring, verified_figure["value"], lines, titles, states, complete
        ),
        # The same figure the assessment view shows, for the Overview (#143).
        "not_met_without_poam": unplanned,
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
    connection: Any,
    project_id: str,
    finding_id: str,
    title: str,
    description: str,
    status: str = "Open",
) -> str:
    action_id, created = str(uuid4()), _now()
    connection.execute(
        """INSERT INTO corrective_actions(
               id, project_id, finding_id, title, description, status, created_at, updated_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (action_id, project_id, finding_id, title, description, status, created, created),
    )
    return action_id


# A POA&M item plans remediation while it is neither Closed nor Withdrawn
# (Draft counts: it exists and is being written).
TERMINAL_POAM_STATUSES = ("Closed", "Withdrawn")


def planned_requirements(connection: Any, project_id: str) -> set[str]:
    """Requirements of this project with at least one open POA&M item."""
    return {
        row["record_id"]
        for row in connection.execute(
            """SELECT DISTINCT f.record_id FROM requirement_findings f
               JOIN corrective_actions a
                 ON a.finding_id = f.finding_id AND a.project_id = f.project_id
               WHERE f.project_id = ? AND a.status NOT IN (?, ?)""",
            (project_id, *TERMINAL_POAM_STATUSES),
        )
    }


def not_met_without_poam(
    connection: Any, project_id: str, not_met_ids: list[str]
) -> dict[str, Any]:
    """NOT MET requirements that are not on any open POA&M item (GitHub issue #143).

    Derived on read, never stored. ``not_met_ids`` are the requirements that
    currently derive Not Met in the assessment, in work-list order; Closed and
    Withdrawn POA&M items do not count as planned.
    """
    planned = planned_requirements(connection, project_id)
    ids = [record_id for record_id in not_met_ids if record_id not in planned]
    return {"count": len(ids), "requirement_ids": ids}


def poam_draft(finding: dict[str, Any], record_id: str, title: str) -> tuple[str, str]:
    """Title and description for a POA&M draft, prefilled from the requirement finding.

    Lists every failed objective with its notes, documented interview or
    observation, and mapped evidence, as the requirement-level finding does.
    """
    lines = [
        f"Remediate {record_id} {title}. Failed assessment objectives:",
    ]
    for objective in finding["failed_objectives"]:
        lines.append("")
        lines.append(f"- {objective['citation']}: {objective['regulation_text']}".rstrip())
        if objective["note"].strip():
            lines.append("  Notes: " + objective["note"].strip().replace("\n", "\n  "))
        observation = objective["interview_observation"].strip()
        if observation:
            lines.append(f"  Interview or observation: {observation}")
        for item in objective["evidence"]:
            rationale = f" ({item['rationale']})" if item["rationale"] else ""
            lines.append(f"  Evidence: {item['name']}{rationale}")
    return f"{record_id} {title}", "\n".join(lines)
