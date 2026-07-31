"""Slice 1a foundation schema.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    schema = """
        CREATE TABLE user_accounts (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL
        );
        CREATE TABLE framework_versions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            record_count INTEGER NOT NULL,
            prompt_count INTEGER NOT NULL,
            declarations_json TEXT NOT NULL
        );
        CREATE TABLE framework_records (
            framework_version_id TEXT NOT NULL REFERENCES framework_versions(id),
            record_id TEXT NOT NULL,
            citation TEXT NOT NULL,
            title TEXT NOT NULL,
            regulation_text TEXT NOT NULL,
            work_area TEXT NOT NULL,
            record_type TEXT NOT NULL,
            parent_id TEXT,
            designation TEXT,
            sort_order INTEGER NOT NULL,
            carries_determination INTEGER NOT NULL,
            PRIMARY KEY (framework_version_id, record_id)
        );
        CREATE TABLE framework_prompts (
            prompt_id TEXT PRIMARY KEY,
            framework_version_id TEXT NOT NULL REFERENCES framework_versions(id),
            original_record_id TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            source TEXT NOT NULL,
            source_detail TEXT NOT NULL,
            cfr_paragraph TEXT NOT NULL,
            group_name TEXT NOT NULL,
            designation TEXT,
            role TEXT NOT NULL,
            role_reason TEXT NOT NULL,
            sort_order INTEGER NOT NULL
        );
        CREATE TABLE clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES clients(id),
            name TEXT NOT NULL,
            framework_version_id TEXT NOT NULL REFERENCES framework_versions(id),
            created_at TEXT NOT NULL
        );
        CREATE TABLE assessments (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL UNIQUE REFERENCES projects(id),
            framework_version_id TEXT NOT NULL REFERENCES framework_versions(id),
            created_at TEXT NOT NULL
        );
        CREATE TABLE determinations (
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            record_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '',
            na_rationale TEXT NOT NULL DEFAULT '',
            addressable_disposition TEXT,
            disposition_reason TEXT NOT NULL DEFAULT '',
            interview_observation TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (assessment_id, record_id)
        );
        CREATE TABLE record_notes (
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            record_id TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (assessment_id, record_id)
        );
        CREATE TABLE prompt_answers (
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            prompt_id TEXT NOT NULL REFERENCES framework_prompts(prompt_id),
            answer TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (assessment_id, prompt_id)
        );
        CREATE TABLE prompt_placements (
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            prompt_id TEXT NOT NULL REFERENCES framework_prompts(prompt_id),
            placement_type TEXT NOT NULL,
            destination_record_id TEXT,
            rule_citation TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL,
            actor_id TEXT NOT NULL REFERENCES user_accounts(id),
            created_at TEXT NOT NULL,
            PRIMARY KEY (assessment_id, prompt_id)
        );
        CREATE TABLE prompt_move_rejections (
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            prompt_id TEXT NOT NULL REFERENCES framework_prompts(prompt_id),
            proposed_record_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            actor_id TEXT NOT NULL REFERENCES user_accounts(id),
            created_at TEXT NOT NULL,
            PRIMARY KEY (assessment_id, prompt_id, proposed_record_id)
        );
        CREATE TABLE evidence_artifacts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            name TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE evidence_mappings (
            id TEXT PRIMARY KEY,
            artifact_id TEXT NOT NULL REFERENCES evidence_artifacts(id),
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            record_id TEXT NOT NULL,
            rationale TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (artifact_id, assessment_id, record_id)
        );
        CREATE TABLE audit_events (
            id TEXT PRIMARY KEY,
            actor_id TEXT NOT NULL REFERENCES user_accounts(id),
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX idx_records_parent
            ON framework_records(framework_version_id, parent_id);
        CREATE INDEX idx_prompts_original
            ON framework_prompts(framework_version_id, original_record_id);
        CREATE INDEX idx_mappings_record
            ON evidence_mappings(assessment_id, record_id);
        CREATE INDEX idx_audit_created ON audit_events(created_at);
        """
    for statement in schema.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for table in (
        "audit_events",
        "evidence_mappings",
        "evidence_artifacts",
        "prompt_move_rejections",
        "prompt_placements",
        "prompt_answers",
        "record_notes",
        "determinations",
        "assessments",
        "projects",
        "clients",
        "framework_prompts",
        "framework_records",
        "framework_versions",
        "user_accounts",
    ):
        op.execute(f"DROP TABLE {table}")
