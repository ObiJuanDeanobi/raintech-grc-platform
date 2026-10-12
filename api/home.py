"""Clients home: one card of figures per client project, for every project at once.

Read-only and derived on read; nothing is stored and there is no schema change
(flow-alignment item 9). The consultant's first screen has to open quickly with
many projects, so this reads in aggregates: one pass over the projects, one over
every determination of the active assessments, and one grouped query each for
evidence dates, evidence activity, open POA&M items, POA&M edits and issued
versions. It never opens or hashes an evidence file and never loads a full
assessment.

The CMMC verified SPRS score is the one figure that runs the official scoring
(``api.cmmc.score``). It is fed statuses already read in bulk and called with
``include_follow_up=False``, so it skips the per-requirement follow-up lookup
and costs a handful of queries per project (partial-credit answers, current
evidence, the requirement and objective lists, POA&M plans). A project with no
decision yet gets no score at all: "Not started", never a negative blank figure.

What is deliberately absent: the projected score, blockers and "left before
issue". Those belong to a project's own Overview.

"Final vN" is the number of issuance snapshots the project has, counting every
issue, including a presentation-only correction that supersedes an earlier one
(ADR 0021 decision 6), up to the current one. The Deliverables "Final versions"
list numbers the same way. The date is the current issue's ``issued_at``.

"Last worked" is the latest of: project and assessment creation, a determination,
a note, a POA&M edit, an evidence upload, an evidence mapping, a new evidence
version, or an issue. Evidence in the recycle bin does not count.
"""

import json
from typing import Any

from api import cmmc, evidence_lifecycle
from api.evidence_lifecycle import DEFAULT_LEAD_DAYS

DECIDED = ("Met", "Not Met", "N/A")
BLANK = "Blank"


def _framework_info(connection: Any) -> dict[str, dict[str, Any]]:
    """Per framework version: name, declarations, deciding-record total and child map."""
    info: dict[str, dict[str, Any]] = {}
    for row in connection.execute("SELECT id, name, declarations_json FROM framework_versions"):
        info[row["id"]] = {
            "name": row["name"],
            "declarations": json.loads(row["declarations_json"]),
            "deciding": 0,
            "children": {},
        }
    for row in connection.execute(
        """SELECT framework_version_id, record_id, parent_id, carries_determination
           FROM framework_records ORDER BY sort_order"""
    ):
        item = info.get(row["framework_version_id"])
        if item is None:
            continue
        if row["carries_determination"]:
            item["deciding"] += 1
        if row["parent_id"]:
            item["children"].setdefault(row["parent_id"], []).append(row["record_id"])
    return info


def _rollup(statuses: list[str], rule: dict[str, Any]) -> str:
    from api.main import _rollup_status

    return _rollup_status(statuses, rule)


def home(connection: Any) -> dict[str, Any]:
    """Cards for all projects, most recently worked first."""
    today = evidence_lifecycle.today()
    frameworks = _framework_info(connection)

    projects = connection.execute(
        """SELECT p.id, p.name, p.created_at, p.framework_version_id,
                  COALESCE(p.evidence_review_lead_days, ?) AS lead_days,
                  c.id AS client_id, c.name AS client_name,
                  a.id AS assessment_id, a.created_at AS assessment_created_at
           FROM projects p
           JOIN clients c ON c.id = p.client_id
           LEFT JOIN project_active_assessments active ON active.project_id = p.id
           LEFT JOIN assessments a ON a.id = active.assessment_id AND a.project_id = p.id
           ORDER BY p.created_at""",
        (DEFAULT_LEAD_DAYS,),
    ).fetchall()

    # Every determination of every active assessment in one pass.
    stored: dict[str, dict[str, str]] = {}
    last_decision: dict[str, str] = {}
    for row in connection.execute(
        """SELECT d.assessment_id, d.record_id, d.status, d.updated_at
           FROM determinations d
           JOIN project_active_assessments active ON active.assessment_id = d.assessment_id"""
    ):
        stored.setdefault(row["assessment_id"], {})[row["record_id"]] = row["status"] or ""
        if row["updated_at"] > last_decision.get(row["assessment_id"], ""):
            last_decision[row["assessment_id"]] = row["updated_at"]

    last_note = {
        row[0]: row[1]
        for row in connection.execute(
            """SELECT n.assessment_id, MAX(n.updated_at) FROM record_notes n
               JOIN project_active_assessments active ON active.assessment_id = n.assessment_id
               GROUP BY n.assessment_id"""
        )
    }
    # Evidence activity per project: uploads, new versions and mappings. Binned evidence
    # (deleted_at) is not work.
    last_evidence: dict[str, str] = {}

    def latest(rows: Any) -> None:
        for row in rows:
            if row[1] and row[1] > last_evidence.get(row[0], ""):
                last_evidence[row[0]] = row[1]

    latest(
        connection.execute(
            """SELECT project_id, MAX(created_at) FROM evidence_artifacts
               WHERE deleted_at IS NULL GROUP BY project_id"""
        )
    )
    latest(
        connection.execute(
            """SELECT ea.project_id, MAX(ev.created_at) FROM evidence_versions ev
               JOIN evidence_artifacts ea ON ea.id = ev.artifact_id
               WHERE ea.deleted_at IS NULL GROUP BY ea.project_id"""
        )
    )
    latest(
        connection.execute(
            """SELECT ea.project_id, MAX(m.created_at) FROM evidence_mappings m
               JOIN evidence_artifacts ea ON ea.id = m.artifact_id
               WHERE ea.deleted_at IS NULL GROUP BY ea.project_id"""
        )
    )
    terminal = ", ".join("?" for _ in cmmc.TERMINAL_POAM_STATUSES)
    open_actions = {
        row[0]: row[1]
        for row in connection.execute(
            f"""SELECT project_id, COUNT(*) FROM corrective_actions
                WHERE status NOT IN ({terminal}) GROUP BY project_id""",
            cmmc.TERMINAL_POAM_STATUSES,
        )
    }
    last_poam = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT project_id, MAX(updated_at) FROM corrective_actions GROUP BY project_id"
        )
    }
    # Evidence review dates against each project's own lead time. Dates only:
    # nothing here opens a stored file.
    evidence = {
        row["project_id"]: (row["expiring"], row["expired"])
        for row in connection.execute(
            """SELECT ea.project_id,
                      SUM(ea.review_date >= :today
                          AND ea.review_date <= date(:today, '+' || COALESCE(
                              p.evidence_review_lead_days, :lead) || ' days')) AS expiring,
                      SUM(ea.review_date < :today) AS expired
               FROM evidence_artifacts ea JOIN projects p ON p.id = ea.project_id
               WHERE ea.deleted_at IS NULL AND ea.review_date IS NOT NULL
                 AND ea.review_date != ''
               GROUP BY ea.project_id""",
            {"today": today.isoformat(), "lead": DEFAULT_LEAD_DAYS},
        )
    }
    issued = {
        row["project_id"]: row
        for row in connection.execute(
            """SELECT c.project_id, c.issued_at,
                      (SELECT COUNT(*) FROM issuance_snapshots s
                        WHERE s.project_id = c.project_id) AS version
               FROM current_issuances c"""
        )
    }

    cards: list[dict[str, Any]] = []
    for project in projects:
        framework = frameworks.get(project["framework_version_id"])
        if framework is None:
            # A project must never vanish from the home: show it, say why it has no figures.
            cards.append(_unavailable_card(project, last_poam, last_evidence))
            continue
        declarations = framework["declarations"]
        scored = bool(declarations.get("scoring"))
        assessment_id = project["assessment_id"]
        states = stored.get(assessment_id, {}) if assessment_id else {}
        deciding_total = framework["deciding"]

        progress: dict[str, Any] | None = None
        sprs: dict[str, Any] | None = None
        status_counts: dict[str, int] | None = None
        if assessment_id:
            counts: dict[str, int] = {}
            for status in states.values():
                counts[status] = counts.get(status, 0) + 1
            decided = sum(counts.get(status, 0) for status in DECIDED)
            progress = {
                "decided": decided,
                "total": deciding_total,
                "percent": round(100 * decided / deciding_total) if deciding_total else 0,
            }
            if scored and decided:
                sprs = _verified_sprs(connection, assessment_id, declarations, framework, states)
            elif not scored:
                shown = [str(s) for s in declarations.get("status_set", []) if s]
                status_counts = {name: counts.get(name, 0) for name in shown}
                status_counts[BLANK] = max(deciding_total - sum(status_counts.values()), 0)

        final = issued.get(project["id"])
        expiring, expired = evidence.get(project["id"], (0, 0))
        worked = max(
            value
            for value in (
                project["created_at"],
                project["assessment_created_at"],
                last_decision.get(assessment_id or ""),
                last_note.get(assessment_id or ""),
                last_evidence.get(project["id"]),
                last_poam.get(project["id"]),
                final["issued_at"] if final else None,
            )
            if value
        )
        cards.append(
            {
                "project_id": project["id"],
                "project_name": project["name"],
                "client_id": project["client_id"],
                "client_name": project["client_name"],
                "framework_id": project["framework_version_id"],
                "framework_name": framework["name"],
                "variant": "cmmc" if scored else "hipaa",
                "assessment_started": bool(assessment_id),
                "progress": progress,
                "verified_sprs": sprs,
                "status_counts": status_counts,
                "final": (
                    {"version": final["version"], "issued_at": final["issued_at"]}
                    if final
                    else None
                ),
                "evidence_expiring": int(expiring or 0),
                "evidence_expired": int(expired or 0),
                "evidence_lead_days": int(project["lead_days"]),
                "open_actions": int(open_actions.get(project["id"], 0)),
                "last_worked_at": worked,
            }
        )
    cards.sort(key=lambda card: (card["last_worked_at"], card["project_id"]), reverse=True)
    return {"generated_on": today.isoformat(), "projects": cards}


def _verified_sprs(
    connection: Any,
    assessment_id: str,
    declarations: dict[str, Any],
    framework: dict[str, Any],
    states: dict[str, str],
) -> dict[str, Any]:
    """The verified SPRS score only (the figure that may be issued).

    Runs the official scoring with requirement statuses derived from the
    determinations already read, so no per-requirement lookup is repeated.
    """
    children = framework["children"]
    rule = declarations["rollup_rule"]

    def derive(_connection: Any, _assessment_id: str, parent_id: str) -> str:
        kids = children.get(parent_id)
        if not kids:
            return ""
        return _rollup([states.get(kid, "") for kid in kids], rule)

    assessment = connection.execute(
        "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    result = cmmc.score(
        connection,
        assessment,
        declarations["scoring"],
        derive,
        include_follow_up=False,
        objective_ids=children,
    )
    return {
        "value": result["verified"]["value"],
        "maximum": result["maximum_score"],
        "minimum": result["minimum_score"],
    }


def _unavailable_card(
    project: Any, last_poam: dict[str, str], last_evidence: dict[str, str]
) -> dict[str, Any]:
    worked = max(
        value
        for value in (
            project["created_at"],
            last_poam.get(project["id"]),
            last_evidence.get(project["id"]),
        )
        if value
    )
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "client_id": project["client_id"],
        "client_name": project["client_name"],
        "framework_id": project["framework_version_id"],
        "framework_name": "Framework unavailable",
        "variant": "unknown",
        "assessment_started": bool(project["assessment_id"]),
        "progress": None,
        "verified_sprs": None,
        "status_counts": None,
        "final": None,
        "evidence_expiring": 0,
        "evidence_expired": 0,
        "evidence_lead_days": int(project["lead_days"]),
        "open_actions": 0,
        "last_worked_at": worked,
    }
