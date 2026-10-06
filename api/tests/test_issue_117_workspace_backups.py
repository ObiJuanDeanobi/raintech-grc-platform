"""Workspace backups, automatic daily/weekly retention, pre-migration backup (Issue #117)."""

import sqlite3
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from api import workspace_backup
from api.database import Database
from api.main import create_app
from api.recovery import recover

ROOT = Path(__file__).resolve().parents[2]


def _setup(tmp_path: Path) -> tuple[TestClient, Path, Path, Path]:
    db, files, backups = tmp_path / "workspace.db", tmp_path / "files", tmp_path / "backups"
    app = create_app(database_path=db, storage_path=files, backup_path=backups)
    return TestClient(app), db, files, backups


def _change(client: TestClient, name: str) -> str:
    client_id = client.post("/api/clients", json={"name": name}).json()["id"]
    project = client.post(f"/api/clients/{client_id}/projects", json={"name": name})
    assert project.status_code == 201
    evidence = client.post(
        f"/api/projects/{project.json()['id']}/evidence",
        files={"file": (f"{name}.txt", b"synthetic evidence", "text/plain")},
    )
    assert evidence.status_code == 201
    return str(project.json()["id"])


def _connect(db: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    return connection


def _run(db: Path, files: Path, backups: Path, kind: str) -> dict[str, Any]:
    with _connect(db) as connection:
        return workspace_backup.create_backup(
            connection, db, files, ROOT / "docs" / "templates", backups, kind
        )


def test_back_up_now_restores_into_a_working_workspace(tmp_path: Path) -> None:
    client, db, files, backups = _setup(tmp_path)
    with client:
        project = _change(client, "Synthetic Backup Client")
        made = client.post("/api/backups")
        assert made.status_code == 201, made.text
        listing = client.get("/api/backups").json()
        assert listing["warning"] is None
        record = listing["backups"][0]
        assert (record["kind"], record["status"]) == ("manual", "complete")
    restored = recover(backups / record["relative_path"], tmp_path / "restored")
    assert any((restored / "files").rglob("*.txt"))
    app = create_app(
        database_path=restored / "workspace.db",
        storage_path=restored / "files",
        backup_path=tmp_path / "restored-backups",
    )
    with TestClient(app) as restored_client:
        names = [p["id"] for c in restored_client.get("/api/clients").json() for p in c["projects"]]
        assert project in names


def test_automatic_backups_are_due_only_after_changes(tmp_path: Path) -> None:
    client, db, files, backups = _setup(tmp_path)
    with client:
        with _connect(db) as connection:
            assert workspace_backup.due(connection) == []  # nothing persisted yet
        _change(client, "First")
        with _connect(db) as connection:
            assert workspace_backup.due(connection) == ["daily", "weekly"]
            results = workspace_backup.run_due(
                connection, db, files, ROOT / "docs" / "templates", backups
            )
            assert [r["status"] for r in results] == ["complete", "complete"]
            # Same day, no new change: nothing is due.
            assert workspace_backup.due(connection) == []
        _change(client, "Second")
        with _connect(db) as connection:
            # A change today does not trigger a second daily backup today.
            assert workspace_backup.due(connection) == []
            tomorrow = datetime.now(UTC) + timedelta(days=1)
            assert workspace_backup.due(connection, tomorrow) == ["daily"]
            next_week = datetime.now(UTC) + timedelta(days=8)
            assert workspace_backup.due(connection, next_week) == ["daily", "weekly"]
            daily = connection.execute(
                "SELECT relative_path FROM workspace_backups WHERE kind='daily'"
            ).fetchone()
        with zipfile.ZipFile(backups / daily["relative_path"]) as archive:
            assert set(archive.namelist()) == {"workspace.db", "application.json", "manifest.json"}


def test_retention_keeps_14_daily_and_2_weekly_and_never_prunes_others(tmp_path: Path) -> None:
    client, db, files, backups = _setup(tmp_path)
    with client:
        _change(client, "Retention")
    for _ in range(16):
        assert _run(db, files, backups, "daily")["status"] == "complete"
    for _ in range(3):
        assert _run(db, files, backups, "weekly")["status"] == "complete"
    assert _run(db, files, backups, "manual")["status"] == "complete"
    with _connect(db) as connection:
        counts = dict(
            connection.execute(
                """SELECT kind || ':' || status, COUNT(*) FROM workspace_backups
                   GROUP BY kind, status"""
            ).fetchall()
        )
        kept = [
            row["relative_path"]
            for row in connection.execute(
                "SELECT relative_path FROM workspace_backups WHERE status='complete'"
            )
        ]
    assert counts == {
        "daily:complete": 14,
        "daily:pruned": 2,
        "weekly:complete": 2,
        "weekly:pruned": 1,
        "manual:complete": 1,
    }
    assert sorted(
        p.relative_to(backups).as_posix() for p in (backups / "workspace").glob("*.zip")
    ) == sorted(kept)


def test_failed_automatic_backup_warns_until_the_next_success(tmp_path: Path) -> None:
    client, db, files, backups = _setup(tmp_path)
    with client:
        _change(client, "Warning")
        blocker = tmp_path / "not-a-directory"
        blocker.write_text("x")
        assert _run(db, files, blocker, "daily")["status"] == "failed"
        warning = client.get("/api/backups").json()["warning"]
        assert warning and "daily" in warning
        assert _run(db, files, backups, "daily")["status"] == "complete"
        assert client.get("/api/backups").json()["warning"] is None


def _config(db: Path, files: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db.as_posix()}")
    config.set_main_option("raintech.managed_storage_root", str(files))
    return config


def test_pending_migration_takes_a_backup_first_and_failure_blocks_it(tmp_path: Path) -> None:
    db, files = tmp_path / "workspace.db", tmp_path / "files"
    database = Database(db, files)
    database.migrate()
    assert not (files / "backups" / "pre-migration").exists()  # nothing pending
    command.downgrade(_config(db, files), "0016")
    database.migrate()
    copies = list((files / "backups" / "pre-migration").glob("*.db"))
    assert len(copies) == 1 and "0016-to-0017" in copies[0].name
    with sqlite3.connect(copies[0]) as copy:
        assert copy.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0016"

    command.downgrade(_config(db, files), "0016")
    blocked = files / "backups" / "pre-migration"
    for earlier in blocked.glob("*.db"):
        earlier.unlink()
    blocked.rmdir()
    blocked.write_text("a file where the backup folder should be")
    with pytest.raises(OSError):
        database.migrate()
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0016"
