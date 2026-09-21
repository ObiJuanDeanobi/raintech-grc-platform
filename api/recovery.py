"""Safe restoration of immutable raintech recovery sets."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "raintech-recovery-set-v1"
APPLICATION = "raintech-grc-platform"


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _safe(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _validate(archive: zipfile.ZipFile) -> tuple[dict[str, Any], dict[str, bytes]]:
    names = archive.namelist()
    if len(names) != len(set(names)) or any(not _safe(name) for name in names):
        raise ValueError("Recovery archive contains unsafe or duplicate paths")
    if "manifest.json" not in names:
        raise ValueError("Recovery archive is missing manifest.json")
    try:
        manifest = json.loads(archive.read("manifest.json"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid recovery manifest") from exc
    if manifest.get("schema") != SCHEMA or not isinstance(manifest.get("items"), list):
        raise ValueError("Unsupported recovery manifest")
    items = manifest["items"]
    paths = [item.get("path") for item in items]
    if any(not isinstance(path, str) or not _safe(path) for path in paths) or len(paths) != len(
        set(paths)
    ):
        raise ValueError("Recovery manifest contains unsafe or duplicate paths")
    expected = set(paths) | {"manifest.json"}
    if set(names) != expected:
        raise ValueError("Recovery archive contents do not match its manifest")
    if json.loads(archive.read("manifest.json")) != manifest:
        raise ValueError("Recovery manifest changed")
    contents: dict[str, bytes] = {}
    for item in items:
        data = archive.read(item["path"])
        if item.get("bytes") != len(data) or item.get("sha256") != _digest(data):
            raise ValueError(f"Recovery item validation failed: {item['path']}")
        contents[item["path"]] = data
    if {"workspace.db", "application.json"} - contents.keys():
        raise ValueError("Recovery set is missing required metadata")
    app = json.loads(contents["application.json"])
    if app.get("application") != APPLICATION or app.get("application_version") != "0.1.0":
        raise ValueError("Recovery application metadata is incompatible")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        temp_path.write_bytes(contents["workspace.db"])
        db = sqlite3.connect(temp_path)
        try:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Workspace database integrity check failed")
            try:
                version = db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            except sqlite3.DatabaseError as exc:
                raise ValueError("Workspace database has no alembic version") from exc
        finally:
            db.close()
    finally:
        temp_path.unlink(missing_ok=True)
    if app.get("schema_version") != version:
        raise ValueError("Application and database schema versions differ")
    return manifest, contents


def recover(archive_path: Path, target: Path) -> Path:
    """Restore *archive_path* into a new, empty *target* directory atomically."""
    archive_path = Path(archive_path).resolve()
    target = Path(target).resolve()
    if target.exists():
        if not target.is_dir() or any(target.iterdir()):
            raise ValueError("Recovery target must be a new or empty directory")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.recovery-", dir=target.parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            _, contents = _validate(archive)
        (staging / "files").mkdir()
        (staging / "recovery-templates").mkdir()
        (staging / "recovery-metadata").mkdir()
        for name, data in contents.items():
            if name == "workspace.db":
                destination = staging / name
            elif name == "application.json":
                destination = staging / "recovery-metadata" / name
            elif name.startswith("managed/"):
                destination = staging / "files" / name.removeprefix("managed/")
            elif name.startswith("template/"):
                destination = staging / "recovery-templates" / name.removeprefix("template/")
            else:
                raise ValueError(f"Unsupported recovery item: {name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        # Manifest is retained exactly as supplied for auditability.
        with zipfile.ZipFile(archive_path) as archive:
            manifest_bytes = archive.read("manifest.json")
            (staging / "recovery-metadata" / "manifest.json").write_bytes(manifest_bytes)
        # An existing empty target is permitted, but must be removed before the
        # final rename so publication remains a single directory replacement.
        if target.exists():
            target.rmdir()
        staging.replace(target)
        return target
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a RainTech recovery set")
    parser.add_argument("archive", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(recover(args.archive, args.target))


if __name__ == "__main__":
    main()
