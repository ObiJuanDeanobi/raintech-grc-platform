"""A withdrawn POA&M item is terminal and must not block the CMMC readiness close."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.tests.test_issue_107_cmmc_ssp import _assess_all, _project
from api.tests.test_issue_108_cmmc_close_issue import (
    FAILING,
    REQUIREMENT,
    _client,
    _codes,
    _readiness,
)


def _set_status(root: Path, status: str) -> None:
    with sqlite3.connect(root / "workspace.db") as connection:
        connection.execute("UPDATE corrective_actions SET status = ?", (status,))


def _with_one_item(client: TestClient, suffix: str) -> tuple[str, str]:
    project, assessment = _project(client, suffix)
    _assess_all(client, project, assessment, failing=FAILING)
    base = f"/api/projects/{project}/assessments/{assessment}/requirements/{REQUIREMENT}"
    created = client.post(f"{base}/poam", json={"title": "Rebuild the authorized user list"})
    assert created.status_code in (200, 201), created.text
    return project, assessment


def test_withdrawn_item_does_not_block_close(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, assessment = _with_one_item(client, "withdrawn")
        assert "poam_open" in _codes(_readiness(client, project, assessment))
        with sqlite3.connect(tmp_path / "workspace.db") as connection:
            action = connection.execute("SELECT id FROM corrective_actions").fetchone()[0]
        withdrawn = client.put(
            f"/api/projects/{project}/corrective-actions/{action}",
            json={"actor_id": "johnathan", "state": "Withdrawn"},
        )
        assert withdrawn.status_code == 200, withdrawn.text
        assert "poam_open" not in _codes(_readiness(client, project, assessment))


@pytest.mark.parametrize("status", ["Open", "Draft", "Waiting"])
def test_unfinished_items_still_block_close(tmp_path: Path, status: str) -> None:
    with _client(tmp_path) as client:
        project, assessment = _with_one_item(client, status.lower())
        _set_status(tmp_path, status)
        assert "poam_open" in _codes(_readiness(client, project, assessment))
