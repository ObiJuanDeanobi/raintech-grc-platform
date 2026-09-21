import json
import sqlite3
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest

from api.recovery import recover


def _archive(path: Path, *, traversal: bool = False) -> Path:
    db = path.with_suffix(".db")
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('head')")
        connection.commit()
    files = {
        "workspace.db": db.read_bytes(),
        "managed/report.txt": b"report",
        "template/base.txt": b"base",
    }
    app = {
        "application": "raintech-grc-platform",
        "application_version": "0.1.0",
        "schema_version": "head",
        "secrets_included": False,
    }
    files["application.json"] = json.dumps(app, separators=(",", ":"), sort_keys=True).encode()
    if traversal:
        files["../escape.txt"] = b"bad"
    manifest = {
        "schema": "raintech-recovery-set-v1",
        "items": [
            {"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()}
            for name, data in files.items()
        ],
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        manifest_json = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
        archive.writestr("manifest.json", manifest_json)
    return path


def test_recover_maps_and_preserves_metadata(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "set.zip")
    target = tmp_path / "restored"
    recover(archive, target)
    assert (target / "workspace.db").is_file()
    assert (target / "files/report.txt").read_bytes() == b"report"
    assert (target / "recovery-templates/base.txt").read_bytes() == b"base"
    assert (target / "recovery-metadata/application.json").is_file()
    assert (target / "recovery-metadata/manifest.json").is_file()


def test_recover_refuses_nonempty_and_traversal(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "set.zip")
    target = tmp_path / "target"
    target.mkdir()
    (target / "sentinel").write_text("keep")
    with pytest.raises(ValueError, match="new or empty"):
        recover(archive, target)
    with pytest.raises(ValueError, match="unsafe"):
        recover(_archive(tmp_path / "bad.zip", traversal=True), tmp_path / "bad-target")


def test_recover_cleans_staging_on_validation_failure(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "bad.zip")
    with zipfile.ZipFile(archive, "a") as zf:
        zf.writestr("managed/report.txt", b"corrupt")
    target = tmp_path / "restored"
    with pytest.raises(ValueError):
        recover(archive, target)
    assert not target.exists()
    assert not list(tmp_path.glob(".restored.recovery-*"))
