"""Verified versus evidence-pending Met (GitHub issue #141, ADR 0019 decision 3).

Specification, Frameworks and Assessments [Amendment 2026-10]: "Final" means at
issue, not at the click. Met may be recorded without evidence; it is then
**evidence pending** and unverified. A Met result is **verified** while it has
current mapped evidence or a documented interview/observation record.

Verification is derived on read, never stored, so a determination is not
rewritten when its support changes. ``CURRENT_MAPPING`` is the one predicate
that decides whether a mapping still counts; evidence staleness and expiry
(issue #142, AC-024) extend that predicate and nothing else.

Staleness is computed on read against ``evidence_lifecycle.today()``: once an
artifact's review date has passed, its mappings stop verifying, so a verified
Met returns to evidence pending and leaves the verified score. The stored
determination and its history are never touched.
"""

from datetime import date
from typing import Any

from api import evidence_lifecycle

VERIFIED = "verified"
EVIDENCE_PENDING = "evidence_pending"

# A mapping counts while it targets this assessment record, pins a stored
# version of a project artifact, that artifact has not been binned, and its
# review date (if any) has not passed (#142). ``:today`` is an ISO date bound by
# the caller. "Passed" matches ``evidence_lifecycle.overdue`` and ``STALE``.
CURRENT_MAPPING = """
    m.target_type = 'assessment_record'
    AND EXISTS (
        SELECT 1 FROM evidence_artifacts ea
        JOIN evidence_versions ev
          ON ev.artifact_id = ea.id AND ev.project_id = ea.project_id
        WHERE ea.id = m.artifact_id AND ev.id = m.evidence_version_id
          AND ea.deleted_at IS NULL
          AND (ea.review_date IS NULL OR ea.review_date = '' OR ea.review_date >= :today)
    )
"""


def met_bases(
    connection: Any, assessment_id: str, today: date | None = None
) -> dict[str, str | None]:
    """Every Met determination in the assessment and what verifies it.

    The value is ``"evidence"``, ``"interview_observation"``, or ``None`` when
    the Met is evidence pending. ``today`` defaults to
    ``evidence_lifecycle.today()``.
    """
    rows = connection.execute(
        f"""SELECT d.record_id,
                   EXISTS (
                       SELECT 1 FROM evidence_mappings m
                       WHERE m.assessment_id = d.assessment_id AND m.record_id = d.record_id
                         AND {CURRENT_MAPPING}
                   ) AS has_evidence,
                   trim(COALESCE(d.interview_observation, '')) != '' AS has_observation
            FROM determinations d
            WHERE d.assessment_id = :assessment_id AND d.status = 'Met'""",
        {
            "assessment_id": assessment_id,
            "today": (today or evidence_lifecycle.today()).isoformat(),
        },
    )
    bases: dict[str, str | None] = {}
    for row in rows:
        if row["has_evidence"]:
            bases[row["record_id"]] = "evidence"
        elif row["has_observation"]:
            bases[row["record_id"]] = "interview_observation"
        else:
            bases[row["record_id"]] = None
    return bases


def state(status: str, children: list[str], bases: dict[str, str | None]) -> str | None:
    """Verification of one record whose (derived) status is ``status``.

    ``children`` are the determination-carrying records that decide it: the
    record itself for an objective, its objectives for a requirement. A
    requirement is verified Met only if every objective is verified Met.
    """
    if status != "Met":
        return None
    if all(bases.get(child) is not None for child in children):
        return VERIFIED
    return EVIDENCE_PENDING
