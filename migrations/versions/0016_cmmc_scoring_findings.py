"""Add CMMC requirement-level findings and partial-implementation scoring input.

A derived Not Met CMMC requirement owns exactly one project-level finding
(ADR 0018: findings carry across revisions). Its history is append-only.
Partial implementation is recorded only for the two requirements that
32 CFR 170.24(c)(2)(i)(B)(4) allows partial credit for.

Revision ID: 0016
Revises: 0015
"""
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE requirement_findings (
        project_id TEXT NOT NULL, record_id TEXT NOT NULL, finding_id TEXT NOT NULL UNIQUE,
        framework_version_id TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(project_id, record_id),
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(finding_id, project_id) REFERENCES findings(id, project_id))"""
    )
    op.execute(
        """CREATE TABLE requirement_finding_events (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, finding_id TEXT NOT NULL,
        assessment_id TEXT NOT NULL,
        event TEXT NOT NULL CHECK(event IN ('opened', 'objectives_changed', 'requirement_cleared')),
        failed_objectives_json TEXT NOT NULL, created_at TEXT NOT NULL,
        FOREIGN KEY(finding_id, project_id) REFERENCES findings(id, project_id),
        FOREIGN KEY(assessment_id, project_id) REFERENCES assessments(id, project_id))"""
    )
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"""CREATE TRIGGER requirement_finding_events_immutable_{action.lower()}
            BEFORE {action} ON requirement_finding_events
            BEGIN SELECT RAISE(ABORT, 'requirement finding history is append-only'); END"""
        )
        op.execute(
            f"""CREATE TRIGGER requirement_findings_immutable_{action.lower()}
            BEFORE {action} ON requirement_findings
            BEGIN SELECT RAISE(ABORT, 'a requirement finding link cannot change'); END"""
        )
    op.execute(
        """CREATE TABLE partial_implementations (
        assessment_id TEXT NOT NULL, project_id TEXT NOT NULL, record_id TEXT NOT NULL,
        implementation TEXT NOT NULL CHECK(implementation IN ('partial', 'none')),
        rationale TEXT NOT NULL CHECK(length(trim(rationale)) > 0),
        actor_id TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(assessment_id, record_id),
        FOREIGN KEY(assessment_id, project_id) REFERENCES assessments(id, project_id),
        FOREIGN KEY(actor_id) REFERENCES user_accounts(id))"""
    )


def downgrade() -> None:
    if op.get_bind().execute(text("SELECT 1 FROM requirement_findings LIMIT 1")).fetchone():
        raise RuntimeError("CMMC requirement findings exist; downgrade would lose finding history.")
    for name in (
        "requirement_finding_events_immutable_update",
        "requirement_finding_events_immutable_delete",
        "requirement_findings_immutable_update",
        "requirement_findings_immutable_delete",
    ):
        op.execute(f"DROP TRIGGER {name}")
    op.execute("DROP TABLE partial_implementations")
    op.execute("DROP TABLE requirement_finding_events")
    op.execute("DROP TABLE requirement_findings")
