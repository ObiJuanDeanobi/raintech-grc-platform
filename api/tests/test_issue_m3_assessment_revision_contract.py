import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


def migration_config(database_path: Path) -> Config:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def connection(database_path: Path) -> sqlite3.Connection:
    result = sqlite3.connect(database_path)
    result.execute("PRAGMA foreign_keys = ON")
    return result


def populate_legacy_database(database_path: Path) -> None:
    with connection(database_path) as db:
        db.executescript(
            """
            INSERT INTO user_accounts(id, display_name) VALUES ('actor', 'Synthetic Actor');
            INSERT INTO framework_versions(
                id, name, record_count, prompt_count, declarations_json
            ) VALUES ('framework', 'Synthetic HIPAA', 0, 0, '{}');
            INSERT INTO clients(id, name, created_at)
            VALUES ('client-a', 'Synthetic Client A', '2026-09-01T00:00:00Z');
            INSERT INTO clients(id, name, created_at)
            VALUES ('client-b', 'Synthetic Client B', '2026-09-01T00:00:00Z');
            INSERT INTO projects(id, client_id, name, framework_version_id, created_at)
            VALUES ('project-a', 'client-a', 'Project A', 'framework', '2026-09-01T00:00:00Z');
            INSERT INTO projects(id, client_id, name, framework_version_id, created_at)
            VALUES ('project-b', 'client-b', 'Project B', 'framework', '2026-09-01T00:00:00Z');
            INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES ('assessment-a', 'project-a', 'framework', '2026-09-01T00:01:00Z');
            INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES ('assessment-b', 'project-b', 'framework', '2026-09-01T00:01:00Z');
            INSERT INTO determinations(assessment_id, record_id, status, updated_at)
            VALUES ('assessment-a', 'synthetic-record', 'Pending', '2026-09-01T00:02:00Z');
            """
        )


def assert_revision(
    db: sqlite3.Connection,
    assessment_id: str,
    project_id: str,
    revision: int,
    predecessor: str | None,
) -> None:
    assert db.execute(
        """SELECT project_id, revision_number, predecessor_assessment_id
        FROM assessment_revisions WHERE assessment_id = ?""",
        (assessment_id,),
    ).fetchone() == (project_id, revision, predecessor)


def foreign_key_targets(db: sqlite3.Connection) -> dict[str, list[str]]:
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {
        table_name: sorted(
            {row[2] for row in db.execute(f'PRAGMA foreign_key_list("{table_name}")')}
        )
        for (table_name,) in tables
    }


def test_populated_upgrade_rebuilds_parent_preserves_dependents_and_can_round_trip(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "workspace.db"
    config = migration_config(database_path)
    command.upgrade(config, "0012")
    populate_legacy_database(database_path)
    with connection(database_path) as db:
        dependent_foreign_keys = foreign_key_targets(db)

    command.upgrade(config, "head")
    with connection(database_path) as db:
        assert foreign_key_targets(db) == dependent_foreign_keys
        assert db.execute("SELECT id, project_id FROM assessments ORDER BY id").fetchall() == [
            ("assessment-a", "project-a"),
            ("assessment-b", "project-b"),
        ]
        assert db.execute(
            "SELECT status FROM determinations WHERE assessment_id='assessment-a'"
        ).fetchone() == ("Pending",)
        assert_revision(db, "assessment-a", "project-a", 1, None)
        assert_revision(db, "assessment-b", "project-b", 1, None)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []

    command.downgrade(config, "0012")
    with connection(database_path) as db:
        assert db.execute("SELECT id, project_id FROM assessments ORDER BY id").fetchall() == [
            ("assessment-a", "project-a"),
            ("assessment-b", "project-b"),
        ]
        assert db.execute(
            "SELECT status FROM determinations WHERE assessment_id='assessment-a'"
        ).fetchone() == ("Pending",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    command.upgrade(config, "head")
    with connection(database_path) as db:
        assert_revision(db, "assessment-a", "project-a", 1, None)
        assert_revision(db, "assessment-b", "project-b", 1, None)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []

        db.execute(
            """INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES ('assessment-a-r2', 'project-a', 'framework', '2026-09-02T00:00:00Z')"""
        )
        assert_revision(db, "assessment-a-r2", "project-a", 2, "assessment-a")
        assert db.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id='project-a'"
        ).fetchone() == ("assessment-a-r2",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []

    before = sqlite3.connect(database_path)
    with before:
        preserved = before.execute("SELECT id, project_id FROM assessments ORDER BY id").fetchall()
    before.close()
    with pytest.raises(Exception, match="Cannot downgrade assessment revisions"):
        command.downgrade(config, "0012")
    with connection(database_path) as db:
        assert (
            db.execute("SELECT id, project_id FROM assessments ORDER BY id").fetchall() == preserved
        )
        assert db.execute("SELECT COUNT(*) FROM assessment_revisions").fetchone() == (3,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_clean_and_one_revision_databases_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "clean.db"
    config = migration_config(database_path)
    command.upgrade(config, "0012")
    command.upgrade(config, "head")
    with connection(database_path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        unique_columns = [
            [row[2] for row in db.execute(f"PRAGMA index_info('{index[1]}')")]
            for index in db.execute("PRAGMA index_list('assessments')")
            if index[2]
        ]
        assert ["project_id"] not in unique_columns
        assert ["id", "project_id"] in unique_columns
    command.downgrade(config, "0012")
    with connection(database_path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' "
            "AND name='assessments_create_initial_revision'"
        ).fetchone() == (1,)
    command.upgrade(config, "head")
    with connection(database_path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_direct_sql_guards_reject_forks_cycles_cross_project_and_pointer_regression(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "guards.db"
    config = migration_config(database_path)
    command.upgrade(config, "0012")
    populate_legacy_database(database_path)
    command.upgrade(config, "head")

    with connection(database_path) as db:
        db.execute(
            """INSERT INTO assessments(id, project_id, framework_version_id, created_at)
            VALUES ('assessment-a-r2', 'project-a', 'framework', '2026-09-02T00:00:00Z')"""
        )
        with pytest.raises(sqlite3.IntegrityError, match="must advance"):
            db.execute(
                "UPDATE project_active_assessments SET assessment_id='assessment-a' "
                "WHERE project_id='project-a'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            db.execute(
                """INSERT INTO assessment_revisions(
                    assessment_id, project_id, revision_number, predecessor_assessment_id
                ) VALUES ('assessment-a-r2', 'project-a', 3, 'assessment-a-r2')"""
            )
        with pytest.raises(sqlite3.IntegrityError, match="must extend"):
            db.execute(
                """INSERT INTO assessment_revisions(
                    assessment_id, project_id, revision_number, predecessor_assessment_id
                ) VALUES ('assessment-b', 'project-a', 2, 'assessment-a')"""
            )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute(
                """INSERT INTO assessment_revisions(
                    assessment_id, project_id, revision_number, predecessor_assessment_id
                ) VALUES ('missing-assessment', 'project-a', 3, 'assessment-a-r2')"""
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute("UPDATE assessments SET created_at='changed' WHERE id='assessment-a'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute("DELETE FROM assessments WHERE id='assessment-a'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute(
                "UPDATE assessment_revisions SET revision_number=9 "
                "WHERE assessment_id='assessment-a'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute("DELETE FROM assessment_revisions WHERE assessment_id='assessment-a'")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY|successor"):
            db.execute(
                "UPDATE project_active_assessments SET assessment_id='assessment-b' "
                "WHERE project_id='project-a'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            db.execute("DELETE FROM project_active_assessments WHERE project_id='project-a'")

        assert_revision(db, "assessment-a", "project-a", 1, None)
        assert_revision(db, "assessment-a-r2", "project-a", 2, "assessment-a")
        assert db.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id='project-a'"
        ).fetchone() == ("assessment-a-r2",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
