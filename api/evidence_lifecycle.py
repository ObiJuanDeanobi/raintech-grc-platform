"""Evidence replacement, recycle bin, and review dates (GitHub issue #119).

Replacement appends an immutable version; existing mappings stay pinned to the
version they were made with. Binning requires no mappings. Purging deletes
stored bytes only and is refused while any source snapshot, package manifest, or
validation still cites the evidence. Backups are self-contained archives, so a
backup's copy is unaffected by purging the live bytes.
"""

import sqlite3
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from api.storage import FileStorage


def _now() -> str:
    return datetime.now(UTC).isoformat()


def artifact_or_404(connection: sqlite3.Connection, project_id: str, artifact_id: str) -> Any:
    row = connection.execute(
        "SELECT * FROM evidence_artifacts WHERE id = ? AND project_id = ?",
        (artifact_id, project_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")
    return row


def versions(connection: sqlite3.Connection, artifact_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT id, version_number, sha256, relative_path, created_at
               FROM evidence_versions WHERE artifact_id = ? ORDER BY version_number""",
            (artifact_id,),
        )
    ]


def overdue(review_date: str | None, today: date | None = None) -> bool:
    if not review_date:
        return False
    return review_date < (today or datetime.now(UTC).date()).isoformat()


def replace(
    connection: sqlite3.Connection,
    storage: FileStorage,
    project_id: str,
    artifact: Any,
    filename: str,
    content: bytes,
) -> dict[str, Any]:
    if artifact["deleted_at"]:
        raise HTTPException(status_code=409, detail="Restore the evidence before replacing it")
    number = len(versions(connection, artifact["id"])) + 1
    # Each version gets its own storage key so earlier bytes are never overwritten.
    relative_path = storage.save(project_id, f"{artifact['id']}-v{number}", filename, content)
    version = {
        "id": str(uuid4()),
        "version_number": number,
        "sha256": sha256(storage.read(relative_path)).hexdigest(),
        "relative_path": relative_path,
        "created_at": _now(),
    }
    connection.execute(
        """INSERT INTO evidence_versions(
               id, artifact_id, project_id, version_number, relative_path, sha256, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            version["id"],
            artifact["id"],
            project_id,
            number,
            relative_path,
            version["sha256"],
            version["created_at"],
        ),
    )
    return version


def mapping_count(connection: sqlite3.Connection, artifact_id: str) -> int:
    return int(
        connection.execute(
            "SELECT COUNT(*) FROM evidence_mappings WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()[0]
    )


def references(connection: sqlite3.Connection, artifact_id: str) -> list[str]:
    """Name every governed record that still cites this artifact's bytes."""
    found: list[str] = []
    for version in versions(connection, artifact_id):
        needles = (version["id"], version["sha256"], version["relative_path"])
        for table, column in (
            ("source_snapshots", "source_json"),
            ("generated_packages", "manifest_json"),
            ("validation_events", "evidence_context_json"),
        ):
            for needle in needles:
                if connection.execute(
                    f"SELECT 1 FROM {table} WHERE instr({column}, ?) > 0 LIMIT 1", (needle,)
                ).fetchone():
                    found.append(table)
    return sorted(set(found))


def purge(storage: FileStorage, connection: sqlite3.Connection, artifact: Any) -> list[str]:
    if not artifact["deleted_at"]:
        raise HTTPException(409, "Only evidence in the recycle bin can be purged")
    cited = references(connection, artifact["id"])
    if cited:
        raise HTTPException(
            status_code=409,
            detail="Issued or governed records still cite this evidence: " + ", ".join(cited),
        )
    paths = [v["relative_path"] for v in versions(connection, artifact["id"])]
    for path in paths:
        storage.delete(path)
    connection.execute(
        "UPDATE evidence_artifacts SET purged_at = ? WHERE id = ?", (_now(), artifact["id"])
    )
    return paths
