import ast
import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from api.database import active_assessment_for_project


@contextmanager
def multi_revision_fixture(
    revision_count: int = 2,
    active_revision_indices: Mapping[str, int] | None = None,
    project_count: int = 1,
    same_client: bool = True,
) -> Iterator[tuple[sqlite3.Connection, dict[str, tuple[str, ...]]]]:
    """Build an isolated schema for revision-selection tests.

    Production intentionally keeps assessments.project_id UNIQUE until the
    revision expansion is enabled. This test-only schema models the target
    revision and active-pointer constraints without changing production DDL.
    """
    if revision_count < 1:
        raise ValueError("revision_count must be at least one")
    if project_count < 1:
        raise ValueError("project_count must be at least one")

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE clients (
            id TEXT PRIMARY KEY
        );
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES clients(id)
        );
        CREATE TABLE assessments (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            UNIQUE(id, project_id)
        );
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
        """
    )
    project_ids = tuple(
        "project-fixture" if project_count == 1 else f"project-fixture-{index}"
        for index in range(1, project_count + 1)
    )
    client_ids = tuple(
        "client-fixture" if same_client else f"client-fixture-{index}"
        for index in range(1, (1 if same_client else project_count) + 1)
    )
    for client_id in client_ids:
        connection.execute("INSERT INTO clients(id) VALUES (?)", (client_id,))

    revisions_by_project: dict[str, tuple[str, ...]] = {}
    for project_index, project_id in enumerate(project_ids):
        client_id = client_ids[0] if same_client else client_ids[project_index]
        connection.execute(
            "INSERT INTO projects(id, client_id) VALUES (?, ?)",
            (project_id, client_id),
        )
        assessment_ids = tuple(
            f"{project_id}-assessment-revision-{index}"
            for index in range(1, revision_count + 1)
        )
        revisions_by_project[project_id] = assessment_ids
        for index, assessment_id in enumerate(assessment_ids, start=1):
            predecessor_id = assessment_ids[index - 2] if index > 1 else None
            connection.execute(
                "INSERT INTO assessments(id, project_id) VALUES (?, ?)",
                (assessment_id, project_id),
            )
            connection.execute(
                "INSERT INTO assessment_revisions"
                "(assessment_id, project_id, revision_number, predecessor_assessment_id) "
                "VALUES (?, ?, ?, ?)",
                (assessment_id, project_id, index, predecessor_id),
            )
        selected_index = (
            revision_count - 1
            if active_revision_indices is None
            else active_revision_indices.get(project_id, revision_count - 1)
        )
        if not 0 <= selected_index < revision_count:
            raise ValueError(f"active revision selection is invalid for {project_id}")
        connection.execute(
            "INSERT INTO project_active_assessments(project_id, assessment_id) VALUES (?, ?)",
            (project_id, assessment_ids[selected_index]),
        )
    try:
        yield connection, revisions_by_project
    finally:
        connection.close()


def _is_implicit_project_assessment_lookup(sql: str) -> bool:
    normalized = re.sub(r"--[^\r\n]*|/\*[\s\S]*?\*/", " ", sql)
    normalized = re.sub(r"'(?:(?:'')|[^'])*'", "''", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    from_match = re.search(r"\bfrom\b(?P<tail>[^;]*)", normalized)
    if from_match is None:
        return False
    statement_tail = from_match.group("tail")
    from_clause = statement_tail.split(" where ", maxsplit=1)[0]
    where_match = re.search(
        r"\bwhere\s+(?P<where>[\s\S]*?)(?:\border\s+by\b|\bgroup\s+by\b|\blimit\b|$)",
        statement_tail,
    )
    where_clause = "" if where_match is None else where_match.group("where")
    uses_active_pointer = bool(
        re.search(
            r"(?:^|\bjoin\b|,)\s*(?:main\.)?project_active_assessments\b",
            from_clause,
        )
    )
    includes_assessments = bool(
        re.search(r"(?:^|\bjoin\b|,)\s*(?:main\.)?assessments\b", from_clause)
    )
    has_project_filter = bool(
        re.search(r"\b(?:\w+\.)?project_id\s*=", where_clause)
    )
    has_assessment_id_filter = bool(re.search(r"\b(?:assessments\.)?id\s*=", where_clause))
    return bool(
        re.search(r"\bselect\b", normalized)
        and includes_assessments
        and has_project_filter
        and not has_assessment_id_filter
        and not uses_active_pointer
    )


def test_test_only_fixture_selects_explicit_active_revision_and_preserves_history() -> None:
    project_id = "project-fixture"
    with multi_revision_fixture(
        revision_count=2,
        active_revision_indices={project_id: 0},
    ) as (connection, revisions_by_project):
        assessment_ids = revisions_by_project[project_id]
        first_id, second_id = assessment_ids
        active = active_assessment_for_project(connection, project_id)
        assert active is not None
        assert active["id"] == first_id

        connection.execute(
            "UPDATE project_active_assessments SET assessment_id = ? WHERE project_id = ?",
            (second_id, project_id),
        )
        active = active_assessment_for_project(connection, project_id)
        assert active is not None
        assert active["id"] == second_id
        history = connection.execute(
            "SELECT assessment_id, revision_number, predecessor_assessment_id "
            "FROM assessment_revisions WHERE project_id = ? ORDER BY revision_number",
            (project_id,),
        ).fetchall()
        assert [tuple(row) for row in history] == [
            (first_id, 1, None),
            (second_id, 2, first_id),
        ]


def test_test_only_fixture_seeds_single_revision_as_active() -> None:
    with multi_revision_fixture(revision_count=1) as (connection, revisions_by_project):
        assessment_ids = revisions_by_project["project-fixture"]
        assert len(assessment_ids) == 1
        active = active_assessment_for_project(connection, "project-fixture")
        assert active is not None
        assert active["id"] == assessment_ids[0]
        revision = connection.execute(
            "SELECT revision_number, predecessor_assessment_id FROM assessment_revisions"
        ).fetchone()
        assert revision is not None
        assert tuple(revision) == (1, None)


def test_test_only_fixture_default_selects_latest_revision_for_default_project() -> None:
    with multi_revision_fixture() as (connection, revisions_by_project):
        assessment_ids = revisions_by_project["project-fixture"]
        active = active_assessment_for_project(connection, "project-fixture")
        assert active is not None
        assert active["id"] == assessment_ids[-1]


def test_test_only_fixture_isolates_projects_for_same_and_different_clients() -> None:
    for same_client in (True, False):
        with multi_revision_fixture(
            revision_count=2,
            project_count=2,
            same_client=same_client,
            active_revision_indices={
                "project-fixture-1": 0,
                "project-fixture-2": 1,
            },
        ) as (connection, revisions_by_project):
            first_project, second_project = tuple(revisions_by_project)
            first_ids = revisions_by_project[first_project]
            second_ids = revisions_by_project[second_project]

            first_active = active_assessment_for_project(connection, first_project)
            second_active = active_assessment_for_project(connection, second_project)
            assert first_active is not None and first_active["id"] == first_ids[0]
            assert second_active is not None and second_active["id"] == second_ids[1]

            connection.execute(
                "UPDATE project_active_assessments SET assessment_id = ? WHERE project_id = ?",
                (first_ids[1], first_project),
            )
            first_active = active_assessment_for_project(connection, first_project)
            second_active = active_assessment_for_project(connection, second_project)
            assert first_active is not None and first_active["id"] == first_ids[1]
            assert second_active is not None and second_active["id"] == second_ids[1]
            clients = connection.execute(
                "SELECT client_id FROM projects ORDER BY id"
            ).fetchall()
            assert [row[0] for row in clients] == (
                ["client-fixture"] * 2
                if same_client
                else ["client-fixture-1", "client-fixture-2"]
            )


def test_production_code_does_not_infer_active_assessment_from_project_id() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    production_sources = sorted(
        source_path
        for source_path in (repository_root / "api").rglob("*.py")
        if "tests" not in source_path.relative_to(repository_root / "api").parts
    )
    offenders: list[str] = []
    for source_path in production_sources:
        syntax_tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(syntax_tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if not _is_implicit_project_assessment_lookup(node.value):
                    continue
                offenders.append(source_path.relative_to(repository_root).as_posix())
                break

    assert not offenders, (
        "Resolve assessment identity through project_active_assessments; "
        "do not infer it from a one-row project lookup: " + ", ".join(offenders)
    )


def test_repository_guard_recognizes_implicit_lookup_and_allows_active_pointer_join() -> None:
    assert _is_implicit_project_assessment_lookup(
        "SELECT * FROM assessments WHERE project_id = ? LIMIT 1"
    )
    assert not _is_implicit_project_assessment_lookup(
        "SELECT assessments.* FROM project_active_assessments active "
        "JOIN assessments ON assessments.id = active.assessment_id "
        "WHERE active.project_id = ?"
    )
    assert not _is_implicit_project_assessment_lookup(
        "SELECT assessments.* FROM assessments JOIN assessment_revisions "
        "ON assessment_revisions.assessment_id = assessments.id "
        "WHERE assessments.id = ? AND assessments.project_id = ?"
    )
    assert _is_implicit_project_assessment_lookup(
        "SELECT * FROM assessments WHERE project_id = ? "
        "/* project_active_assessments is mentioned here, but not joined */"
    )
    assert _is_implicit_project_assessment_lookup(
        "SELECT * FROM assessments -- JOIN project_active_assessments active\n"
        "WHERE assessments.project_id = ?"
    )
