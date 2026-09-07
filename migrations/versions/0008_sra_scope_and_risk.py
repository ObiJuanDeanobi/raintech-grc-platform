"""Add declaration-driven HIPAA SRA scope and project-scoped risks.

Revision ID: 0008
Revises: 0007
"""

import json
from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FRAMEWORK_ID = "hipaa-45cfr164-2026-07-01"
SRA_DECLARATION = {
    "anchor_record_id": "164.308(a)(1)(ii)(A)",
    "work_area": "Security Risk Analysis",
    "scope_targets": [
        {"scope_type": "system", "profile_item_types": ["scope_item"]},
        {"scope_type": "location", "profile_item_types": ["location"]},
        {"scope_type": "vendor", "profile_item_types": ["external_service"]},
        {
            "scope_type": "flow",
            "profile_item_types": ["business_process"],
            "profile_sections": [
                "flows",
                "information_flows",
                "data_flows",
                "ephi_flows",
            ],
        },
    ],
    "risk_required_fields": [
        "threat",
        "vulnerability",
        "cia_impact",
        "safeguards",
        "owner",
        "status",
        "reviewed_by",
        "reviewed_at",
    ],
    "acceptance_required_fields": ["acceptance_rationale", "owner", "review_date"],
    "approval_required_bands": ["High", "Critical"],
    "approval_required_fields": ["approver", "approved_at"],
}


def upgrade() -> None:
    declaration_json = json.dumps(SRA_DECLARATION, separators=(",", ":"))
    escaped = declaration_json.replace("'", "''")
    op.execute(
        "UPDATE framework_versions "
        f"SET declarations_json = json_set(declarations_json, '$.sra', json('{escaped}')) "
        f"WHERE id = '{FRAMEWORK_ID}'"
    )
    op.execute(
        """
        CREATE TABLE sra_scope_reviews (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            profile_version_id TEXT NOT NULL,
            scope_type TEXT NOT NULL,
            target_key TEXT NOT NULL,
            included INTEGER NOT NULL CHECK(included IN (0, 1)),
            exclusion_rationale TEXT NOT NULL DEFAULT '',
            reviewed_by TEXT NOT NULL CHECK(length(trim(reviewed_by)) > 0),
            reviewed_at TEXT NOT NULL CHECK(length(trim(reviewed_at)) > 0),
            UNIQUE(id, project_id),
            UNIQUE(project_id, profile_version_id, scope_type, target_key),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(profile_version_id, project_id)
                REFERENCES profile_versions(id, project_id),
            CHECK(included = 1 OR length(trim(exclusion_rationale)) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE risks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            assessment_id TEXT NOT NULL,
            profile_version_id TEXT NOT NULL,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            threat TEXT NOT NULL CHECK(length(trim(threat)) > 0),
            vulnerability TEXT NOT NULL CHECK(length(trim(vulnerability)) > 0),
            cia_impact TEXT NOT NULL CHECK(length(trim(cia_impact)) > 0),
            safeguards TEXT NOT NULL CHECK(length(trim(safeguards)) > 0),
            corrective_action TEXT NOT NULL DEFAULT '',
            treatment TEXT NOT NULL
                CHECK(treatment IN ('corrective_action', 'acceptance')),
            owner TEXT NOT NULL CHECK(length(trim(owner)) > 0),
            status TEXT NOT NULL CHECK(length(trim(status)) > 0),
            review_date TEXT,
            inherent_likelihood INTEGER NOT NULL CHECK(inherent_likelihood BETWEEN 1 AND 5),
            inherent_impact INTEGER NOT NULL CHECK(inherent_impact BETWEEN 1 AND 5),
            residual_likelihood INTEGER NOT NULL CHECK(residual_likelihood BETWEEN 1 AND 5),
            residual_impact INTEGER NOT NULL CHECK(residual_impact BETWEEN 1 AND 5),
            acceptance_rationale TEXT NOT NULL DEFAULT '',
            approver TEXT NOT NULL DEFAULT '',
            approved_at TEXT,
            reviewed_by TEXT NOT NULL CHECK(length(trim(reviewed_by)) > 0),
            reviewed_at TEXT NOT NULL CHECK(length(trim(reviewed_at)) > 0),
            created_by TEXT NOT NULL REFERENCES user_accounts(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(id, project_id),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(assessment_id, project_id)
                REFERENCES assessments(id, project_id),
            FOREIGN KEY(profile_version_id, project_id)
                REFERENCES profile_versions(id, project_id),
            CHECK(
                treatment != 'acceptance'
                OR (length(trim(acceptance_rationale)) > 0 AND review_date IS NOT NULL)
            ),
            CHECK(
                treatment != 'acceptance'
                OR (inherent_likelihood * inherent_impact < 10
                 AND residual_likelihood * residual_impact < 10)
                OR (length(trim(approver)) > 0 AND approved_at IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE risk_evidence_mappings (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            risk_id TEXT NOT NULL,
            artifact_id TEXT NOT NULL,
            evidence_version_id TEXT NOT NULL,
            rationale TEXT NOT NULL CHECK(length(trim(rationale)) > 0),
            created_by TEXT NOT NULL REFERENCES user_accounts(id),
            created_at TEXT NOT NULL,
            UNIQUE(id, project_id),
            UNIQUE(risk_id, evidence_version_id),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(risk_id, project_id) REFERENCES risks(id, project_id),
            FOREIGN KEY(artifact_id, project_id)
                REFERENCES evidence_artifacts(id, project_id),
            FOREIGN KEY(evidence_version_id, artifact_id, project_id)
                REFERENCES evidence_versions(id, artifact_id, project_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_sra_scope_project ON sra_scope_reviews(project_id, profile_version_id)"
    )
    op.execute("CREATE INDEX idx_risks_project ON risks(project_id, assessment_id)")
    op.execute(
        "CREATE INDEX idx_risk_evidence_project ON risk_evidence_mappings(project_id, risk_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE risk_evidence_mappings")
    op.execute("DROP TABLE risks")
    op.execute("DROP TABLE sra_scope_reviews")
    op.execute(
        "UPDATE framework_versions "
        "SET declarations_json = json_remove(declarations_json, '$.sra') "
        f"WHERE id = '{FRAMEWORK_ID}'"
    )
