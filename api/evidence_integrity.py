"""Verify stored evidence versions against their recorded SHA-256 (Issue #106)."""

import io
import json
import sqlite3
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

HEX_SHA256_LENGTH = 64


def _verify_row(row: sqlite3.Row, storage_root: Path) -> dict[str, Any]:
    recorded = (row["sha256"] or "").strip().lower()
    item = {
        "evidence_version_id": row["id"],
        "artifact_id": row["artifact_id"],
        "artifact_name": row["artifact_name"],
        "version_number": row["version_number"],
        "sha256": recorded,
        "result": "verified",
    }
    if len(recorded) != HEX_SHA256_LENGTH:
        item["result"] = "unhashed"
        return item
    root = storage_root.resolve()
    path = (storage_root / row["relative_path"]).resolve()
    if root not in path.parents or not path.is_file():
        item["result"] = "missing"
    elif sha256(path.read_bytes()).hexdigest() != recorded:
        item["result"] = "mismatch"
    return item


def verify_assessment_evidence(
    connection: sqlite3.Connection, storage_root: Path, project_id: str, assessment_id: str
) -> list[dict[str, Any]]:
    """Every evidence version mapped to an assessment record, with its verification result."""
    rows = connection.execute(
        """SELECT DISTINCT v.id, v.artifact_id, v.version_number, v.sha256, v.relative_path,
                  a.name AS artifact_name
           FROM evidence_mappings m
           JOIN evidence_versions v
             ON v.id = m.evidence_version_id AND v.project_id = m.project_id
           JOIN evidence_artifacts a ON a.id = v.artifact_id AND a.project_id = v.project_id
           WHERE m.project_id = ? AND m.assessment_id = ? AND m.target_type = 'assessment_record'
           ORDER BY a.name, v.version_number""",
        (project_id, assessment_id),
    ).fetchall()
    return [_verify_row(row, storage_root) for row in rows]


def evidence_blockers(index: list[dict[str, Any]]) -> list[str]:
    return [
        f"Evidence {item['artifact_name']} v{item['version_number']} failed verification: "
        f"{item['result']}"
        for item in index
        if item["result"] != "verified"
    ]


def export_selected_evidence(
    connection: sqlite3.Connection,
    storage_root: Path,
    project_id: str,
    evidence_version_ids: list[str],
) -> bytes:
    """Return a ZIP of the selected versions plus an index, or raise without partial output."""
    if not evidence_version_ids:
        raise ValueError("Select at least one evidence version")
    placeholders = ",".join("?" for _ in evidence_version_ids)
    rows = connection.execute(
        f"""SELECT v.id, v.artifact_id, v.version_number, v.sha256, v.relative_path,
                   a.name AS artifact_name
            FROM evidence_versions v
            JOIN evidence_artifacts a ON a.id = v.artifact_id AND a.project_id = v.project_id
            WHERE v.project_id = ? AND v.id IN ({placeholders})
            ORDER BY a.name, v.version_number""",
        (project_id, *evidence_version_ids),
    ).fetchall()
    if len(rows) != len(set(evidence_version_ids)):
        raise LookupError("Evidence version not found")
    index = [_verify_row(row, storage_root) for row in rows]
    failures = evidence_blockers(index)
    if failures:
        raise ValueError("; ".join(failures))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for row, item in zip(rows, index, strict=True):
            name = f"evidence/{item['evidence_version_id']}-{Path(row['artifact_name']).name}"
            archive.writestr(name, (storage_root / row["relative_path"]).read_bytes())
            item["path"] = name
        archive.writestr(
            "evidence-index.json",
            json.dumps(
                {
                    "project_id": project_id,
                    "exported_at": datetime.now(UTC).isoformat(),
                    "items": index,
                },
                indent=2,
                sort_keys=True,
            ),
        )
    return buffer.getvalue()
