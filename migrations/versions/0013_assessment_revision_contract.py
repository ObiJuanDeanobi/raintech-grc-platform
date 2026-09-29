"""Allow sequential immutable assessment revisions per project.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rebuild_assessments(*, unique_project: bool) -> None:
    unique_project_sql = " UNIQUE" if unique_project else ""
    # SQLite keeps dependent FK declarations bound to the stable table name.
    # Defer checks while the parent table is replaced with the same primary keys.
    op.execute("PRAGMA defer_foreign_keys = ON")
    op.execute(
        f"""CREATE TABLE assessments_revision_contract (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL{unique_project_sql} REFERENCES projects(id),
            framework_version_id TEXT NOT NULL REFERENCES framework_versions(id),
            created_at TEXT NOT NULL
        )"""
    )
    op.execute(
        """INSERT INTO assessments_revision_contract(
            id, project_id, framework_version_id, created_at
        ) SELECT id, project_id, framework_version_id, created_at FROM assessments"""
    )
    op.execute("DROP TABLE assessments")
    op.execute("ALTER TABLE assessments_revision_contract RENAME TO assessments")
    op.execute("CREATE UNIQUE INDEX uq_assessments_project_identity ON assessments(id, project_id)")


def upgrade() -> None:
    op.execute("DROP TRIGGER assessments_create_initial_revision")
    _rebuild_assessments(unique_project=False)

    op.execute(
        """CREATE UNIQUE INDEX idx_assessment_revisions_one_child
        ON assessment_revisions(project_id, predecessor_assessment_id)
        WHERE predecessor_assessment_id IS NOT NULL"""
    )
    op.execute(
        """CREATE TRIGGER assessment_revisions_insert_guard
        BEFORE INSERT ON assessment_revisions
        WHEN (
            EXISTS (SELECT 1 FROM project_active_assessments a
                    WHERE a.project_id = NEW.project_id)
            AND NOT EXISTS (
                SELECT 1
                FROM project_active_assessments a
                JOIN assessment_revisions current
                  ON current.assessment_id = a.assessment_id
                 AND current.project_id = a.project_id
                WHERE a.project_id = NEW.project_id
                  AND NEW.predecessor_assessment_id = a.assessment_id
                  AND NEW.revision_number = current.revision_number + 1
            )
        ) OR (
            NOT EXISTS (SELECT 1 FROM project_active_assessments a
                        WHERE a.project_id = NEW.project_id)
            AND (NEW.revision_number != 1 OR NEW.predecessor_assessment_id IS NOT NULL
                 OR EXISTS (SELECT 1 FROM assessment_revisions r
                            WHERE r.project_id = NEW.project_id))
        )
        BEGIN
            SELECT RAISE(ABORT, 'assessment revision must extend the active revision');
        END"""
    )
    op.execute(
        """CREATE TRIGGER assessment_revisions_advance_active
        AFTER INSERT ON assessment_revisions
        WHEN NEW.predecessor_assessment_id IS NOT NULL
        BEGIN
            UPDATE project_active_assessments
            SET assessment_id = NEW.assessment_id
            WHERE project_id = NEW.project_id;
        END"""
    )
    op.execute(
        """CREATE TRIGGER assessment_revisions_create_active
        AFTER INSERT ON assessment_revisions
        WHEN NEW.predecessor_assessment_id IS NULL
        BEGIN
            INSERT INTO project_active_assessments(project_id, assessment_id)
            VALUES (NEW.project_id, NEW.assessment_id);
        END"""
    )
    op.execute(
        """CREATE TRIGGER assessments_create_next_revision
        AFTER INSERT ON assessments
        BEGIN
            INSERT INTO assessment_revisions(
                assessment_id, project_id, revision_number, predecessor_assessment_id
            )
            SELECT NEW.id, NEW.project_id,
                   COALESCE(current.revision_number + 1, 1), active.assessment_id
            FROM (SELECT 1) seed
            LEFT JOIN project_active_assessments active
              ON active.project_id = NEW.project_id
            LEFT JOIN assessment_revisions current
              ON current.project_id = active.project_id
             AND current.assessment_id = active.assessment_id;
        END"""
    )
    op.execute(
        """CREATE TRIGGER project_active_assessments_successor_guard
        BEFORE UPDATE OF assessment_id ON project_active_assessments
        WHEN NOT EXISTS (
            SELECT 1 FROM assessment_revisions successor
            JOIN assessment_revisions current
              ON current.project_id = successor.project_id
             AND current.assessment_id = OLD.assessment_id
            WHERE successor.project_id = OLD.project_id
              AND successor.assessment_id = NEW.assessment_id
              AND successor.predecessor_assessment_id = OLD.assessment_id
              AND successor.revision_number = current.revision_number + 1
        )
        BEGIN
            SELECT RAISE(ABORT, 'active assessment pointer must advance to its successor');
        END"""
    )
    op.execute(
        """CREATE TRIGGER project_active_assessments_root_guard
        BEFORE INSERT ON project_active_assessments
        WHEN NOT EXISTS (
            SELECT 1 FROM assessment_revisions root
            WHERE root.project_id = NEW.project_id
              AND root.assessment_id = NEW.assessment_id
              AND root.revision_number = 1
              AND root.predecessor_assessment_id IS NULL
        )
        BEGIN
            SELECT RAISE(ABORT, 'active assessment pointer must start at its root');
        END"""
    )
    for table in ("assessments", "assessment_revisions"):
        op.execute(
            f"""CREATE TRIGGER {table}_immutable_update
            BEFORE UPDATE ON {table}
            BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END"""
        )
        op.execute(
            f"""CREATE TRIGGER {table}_immutable_delete
            BEFORE DELETE ON {table}
            BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END"""
        )


def downgrade() -> None:
    bind = op.get_bind()
    successors = bind.exec_driver_sql(
        """SELECT project_id, COUNT(*) FROM assessments
        GROUP BY project_id HAVING COUNT(*) > 1 LIMIT 1"""
    ).first()
    if successors is not None:
        raise RuntimeError(
            "Cannot downgrade assessment revisions while successor assessments exist"
        )

    for trigger in (
        "assessments_immutable_delete",
        "assessments_immutable_update",
        "assessment_revisions_immutable_delete",
        "assessment_revisions_immutable_update",
        "project_active_assessments_root_guard",
        "project_active_assessments_successor_guard",
        "assessments_create_next_revision",
        "assessment_revisions_create_active",
        "assessment_revisions_advance_active",
        "assessment_revisions_insert_guard",
    ):
        op.execute(f"DROP TRIGGER {trigger}")
    op.execute("DROP INDEX idx_assessment_revisions_one_child")
    _rebuild_assessments(unique_project=True)
    op.execute(
        """CREATE TRIGGER assessments_create_initial_revision
        AFTER INSERT ON assessments
        BEGIN
            INSERT INTO assessment_revisions(
                assessment_id, project_id, revision_number, predecessor_assessment_id
            ) VALUES (NEW.id, NEW.project_id, 1, NULL);
            INSERT INTO project_active_assessments(project_id, assessment_id)
            VALUES (NEW.project_id, NEW.id);
        END"""
    )
