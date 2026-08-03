"""Question-level working records for practitioner testing.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE prompt_answers ADD COLUMN status TEXT NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE prompt_answers ADD COLUMN na_rationale TEXT NOT NULL DEFAULT ''")
    op.execute(
        "ALTER TABLE prompt_answers ADD COLUMN interview_observation TEXT NOT NULL DEFAULT ''"
    )
    op.execute(
        """
        CREATE TABLE prompt_evidence_mappings (
            id TEXT PRIMARY KEY,
            artifact_id TEXT NOT NULL REFERENCES evidence_artifacts(id),
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            prompt_id TEXT NOT NULL REFERENCES framework_prompts(prompt_id),
            rationale TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE (artifact_id, assessment_id, prompt_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_prompt_mappings_prompt
            ON prompt_evidence_mappings(assessment_id, prompt_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX idx_prompt_mappings_prompt")
    op.execute("DROP TABLE prompt_evidence_mappings")
    op.execute("ALTER TABLE prompt_answers DROP COLUMN interview_observation")
    op.execute("ALTER TABLE prompt_answers DROP COLUMN na_rationale")
    op.execute("ALTER TABLE prompt_answers DROP COLUMN status")
