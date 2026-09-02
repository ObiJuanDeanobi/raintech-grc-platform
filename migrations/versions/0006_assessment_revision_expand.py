"""Add assessment revision metadata and project-scoped active pointers.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    schema = """
        CREATE TABLE assessment_revisions (
            assessment_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            revision_number INTEGER NOT NULL CHECK(revision_number > 0),
            predecessor_assessment_id TEXT,
            UNIQUE(project_id, revision_number),
            UNIQUE(assessment_id, project_id),
            FOREIGN KEY(assessment_id, project_id)
                REFERENCES assessments(id, project_id),
            FOREIGN KEY(predecessor_assessment_id, project_id)
                REFERENCES assessment_revisions(assessment_id, project_id),
            CHECK(predecessor_assessment_id IS NULL OR predecessor_assessment_id != assessment_id)
        );
        CREATE TABLE project_active_assessments (
            project_id TEXT PRIMARY KEY REFERENCES projects(id),
            assessment_id TEXT NOT NULL,
            FOREIGN KEY(assessment_id, project_id)
                REFERENCES assessment_revisions(assessment_id, project_id)
        );
        CREATE INDEX idx_assessment_revisions_predecessor
            ON assessment_revisions(project_id, predecessor_assessment_id);
    """
    for statement in schema.split(";"):
        if statement.strip():
            op.execute(statement)

    op.execute(
        """
        INSERT INTO assessment_revisions(
            assessment_id, project_id, revision_number, predecessor_assessment_id
        )
        SELECT id, project_id, 1, NULL
        FROM assessments
        """
    )
    op.execute(
        """
        INSERT INTO project_active_assessments(project_id, assessment_id)
        SELECT project_id, id
        FROM assessments
        """
    )
    op.execute(
        """
        CREATE TRIGGER assessments_create_initial_revision
        AFTER INSERT ON assessments
        BEGIN
            INSERT INTO assessment_revisions(
                assessment_id, project_id, revision_number, predecessor_assessment_id
            ) VALUES (NEW.id, NEW.project_id, 1, NULL);
            INSERT INTO project_active_assessments(project_id, assessment_id)
            VALUES (NEW.project_id, NEW.id);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER project_active_assessments_cannot_delete
        BEFORE DELETE ON project_active_assessments
        BEGIN
            SELECT RAISE(ABORT, 'Active assessment pointers cannot be deleted');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER project_active_assessments_cannot_change_project
        BEFORE UPDATE OF project_id ON project_active_assessments
        WHEN NEW.project_id != OLD.project_id
        BEGIN
            SELECT RAISE(ABORT, 'Active assessment pointer projects cannot change');
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER project_active_assessments_cannot_change_project")
    op.execute("DROP TRIGGER project_active_assessments_cannot_delete")
    op.execute("DROP TRIGGER assessments_create_initial_revision")
    op.execute("DROP INDEX idx_assessment_revisions_predecessor")
    op.execute("DROP TABLE project_active_assessments")
    op.execute("DROP TABLE assessment_revisions")
