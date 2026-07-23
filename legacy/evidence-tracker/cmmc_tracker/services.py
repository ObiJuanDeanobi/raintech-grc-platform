from __future__ import annotations

import csv
import hashlib
import io
import shutil
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

from openpyxl import Workbook

from .db import connect
from .naming import generated_evidence_filename, normalize_extension, sanitize_filename_part
from .paths import evidence_dir, exports_dir


def domain_export_folder(sort_order: int, domain_name: str) -> str:
    return f"{sort_order} - {sanitize_filename_part(domain_name)}"


def store_upload(
    fileobj,
    original_filename: str,
    title: str,
    source: str = "",
    notes: str = "",
    capture_date: str | None = None,
) -> int:
    evidence_dir().mkdir(parents=True, exist_ok=True)
    original_filename = original_filename or "evidence.bin"
    extension = normalize_extension(original_filename)
    content = fileobj.read()
    digest = hashlib.sha256(content).hexdigest()
    stored_relative = f"evidence/{digest}{extension}"
    stored_absolute = evidence_dir() / f"{digest}{extension}"
    if not stored_absolute.exists():
        stored_absolute.write_bytes(content)

    evidence_title = title.strip() if title.strip() else Path(original_filename).stem
    capture_date = capture_date or date.today().isoformat()
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with connect() as conn:
        existing = conn.execute("SELECT id FROM evidence WHERE sha256 = ?", (digest,)).fetchone()
        if existing:
            return int(existing["id"])
        cur = conn.execute(
            """
            INSERT INTO evidence(
                title, original_filename, stored_path, extension, sha256,
                capture_date, source, notes, uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_title,
                original_filename,
                stored_relative,
                extension,
                digest,
                capture_date,
                source.strip(),
                notes.strip(),
                now,
            ),
        )
        return int(cur.lastrowid)


def _store_file_bytes(content: bytes, original_filename: str) -> tuple[str, str, str]:
    evidence_dir().mkdir(parents=True, exist_ok=True)
    original_filename = original_filename or "evidence.bin"
    extension = normalize_extension(original_filename)
    digest = hashlib.sha256(content).hexdigest()
    stored_relative = f"evidence/{digest}{extension}"
    stored_absolute = evidence_dir() / f"{digest}{extension}"
    if not stored_absolute.exists():
        stored_absolute.write_bytes(content)
    return stored_relative, extension, digest


def _remove_file_if_unreferenced(conn, stored_path: str) -> None:
    if not stored_path:
        return
    references = conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE stored_path = ?",
        (stored_path,),
    ).fetchone()[0]
    if references:
        return
    path = evidence_dir().parent / stored_path
    if path.exists():
        path.unlink()


def _refresh_statuses_for_objectives(conn, objective_ids: list[str]) -> None:
    for objective_id in objective_ids:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM objective_evidence WHERE objective_id = ?",
            (objective_id,),
        ).fetchone()[0]
        conn.execute(
            """
            UPDATE objective_status
            SET status = ?, updated_at = datetime('now')
            WHERE objective_id = ?
            """,
            ("Captured" if remaining else "Not Captured", objective_id),
        )


def delete_evidence(evidence_id: int) -> bool:
    with connect() as conn:
        evidence = conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
        if not evidence:
            return False
        objective_ids = [
            row["objective_id"]
            for row in conn.execute(
                "SELECT objective_id FROM objective_evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchall()
        ]
        stored_path = evidence["stored_path"]
        conn.execute("DELETE FROM objective_evidence WHERE evidence_id = ?", (evidence_id,))
        conn.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
        _refresh_statuses_for_objectives(conn, objective_ids)
        _remove_file_if_unreferenced(conn, stored_path)
        return True


def replace_evidence(
    evidence_id: int,
    fileobj,
    original_filename: str,
    title: str = "",
    source: str = "",
    notes: str = "",
) -> int | None:
    content = fileobj.read()
    stored_relative, extension, digest = _store_file_bytes(content, original_filename)
    today = date.today().isoformat()
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with connect() as conn:
        evidence = conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
        if not evidence:
            return None
        old_stored_path = evidence["stored_path"]
        mapped_objective_ids = [
            row["objective_id"]
            for row in conn.execute(
                "SELECT objective_id FROM objective_evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchall()
        ]
        existing = conn.execute(
            "SELECT id FROM evidence WHERE sha256 = ? AND id <> ?",
            (digest, evidence_id),
        ).fetchone()
        if existing:
            replacement_id = int(existing["id"])
            for objective_id in mapped_objective_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO objective_evidence(objective_id, evidence_id) VALUES(?, ?)",
                    (objective_id, replacement_id),
                )
            conn.execute("DELETE FROM objective_evidence WHERE evidence_id = ?", (evidence_id,))
            conn.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
            _refresh_statuses_for_objectives(conn, mapped_objective_ids)
            _remove_file_if_unreferenced(conn, old_stored_path)
            return replacement_id

        conn.execute(
            """
            UPDATE evidence
            SET title = ?,
                original_filename = ?,
                stored_path = ?,
                extension = ?,
                sha256 = ?,
                capture_date = ?,
                source = ?,
                notes = ?,
                uploaded_at = ?
            WHERE id = ?
            """,
            (
                title.strip() or evidence["title"],
                original_filename or evidence["original_filename"],
                stored_relative,
                extension,
                digest,
                today,
                source.strip() or evidence["source"],
                notes.strip() or evidence["notes"],
                now,
                evidence_id,
            ),
        )
        _refresh_statuses_for_objectives(conn, mapped_objective_ids)
        if old_stored_path != stored_relative:
            _remove_file_if_unreferenced(conn, old_stored_path)
        return evidence_id


def attach_evidence(objective_id: str, evidence_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO objective_evidence(objective_id, evidence_id) VALUES(?, ?)",
            (objective_id, evidence_id),
        )
        conn.execute(
            """
            UPDATE objective_status
            SET status = 'Captured', updated_at = datetime('now')
            WHERE objective_id = ?
            """,
            (objective_id,),
        )


def detach_evidence(objective_id: str, evidence_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "DELETE FROM objective_evidence WHERE objective_id = ? AND evidence_id = ?",
            (objective_id, evidence_id),
        )
        remaining = conn.execute(
            "SELECT COUNT(*) FROM objective_evidence WHERE objective_id = ?",
            (objective_id,),
        ).fetchone()[0]
        if remaining == 0:
            conn.execute(
                """
                UPDATE objective_status
                SET status = 'Not Captured', updated_at = datetime('now')
                WHERE objective_id = ?
                """,
                (objective_id,),
            )


def completion_rows():
    with connect() as conn:
        return conn.execute(
            """
            SELECT
                d.name AS domain,
                r.id AS requirement_id,
                r.name AS requirement_name,
                o.id AS objective_id,
                o.text AS objective_text,
                os.status,
                os.notes,
                COUNT(oe.evidence_id) AS evidence_count
            FROM objectives o
            JOIN requirements r ON r.id = o.requirement_id
            JOIN domains d ON d.code = r.domain_code
            JOIN objective_status os ON os.objective_id = o.id
            LEFT JOIN objective_evidence oe ON oe.objective_id = o.id
            GROUP BY o.id
            ORDER BY d.sort_order, r.id, o.letter
            """
        ).fetchall()


def completion_csv() -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Domain",
            "Requirement ID",
            "Requirement Name",
            "Objective ID",
            "Objective Text",
            "Status",
            "Evidence Count",
            "Missing Evidence",
            "Notes",
        ]
    )
    for row in completion_rows():
        writer.writerow(
            [
                row["domain"],
                row["requirement_id"],
                row["requirement_name"],
                row["objective_id"],
                row["objective_text"],
                row["status"],
                row["evidence_count"],
                "Yes" if row["evidence_count"] == 0 else "No",
                row["notes"],
            ]
        )
    return output.getvalue()


def completion_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Completion"
    rows = list(csv.reader(io.StringIO(completion_csv())))
    for row in rows:
        ws.append(row)
    for column_cells in ws.columns:
        width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 70)
        ws.column_dimensions[column_cells[0].column_letter].width = width
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def export_zip() -> Path:
    exports_dir().mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = exports_dir() / f"cmmc_l2_evidence_export_{timestamp}.zip"
    manifest = io.StringIO(newline="")
    writer = csv.writer(manifest)
    writer.writerow(
        [
            "Domain",
            "Requirement ID",
            "Objective ID",
            "Status",
            "Evidence ID",
            "Evidence Title",
            "Original Filename",
            "Export Filename",
            "SHA256",
            "Capture Date",
            "Notes",
        ]
    )
    used_by_folder: dict[str, set[str]] = {}
    with connect() as conn, zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        rows = conn.execute(
            """
            SELECT
                d.sort_order AS domain_order,
                d.name AS domain,
                r.id AS requirement_id,
                o.id AS objective_id,
                os.status,
                e.id AS evidence_id,
                e.title,
                e.original_filename,
                e.stored_path,
                e.extension,
                e.sha256,
                e.capture_date,
                e.notes
            FROM objective_evidence oe
            JOIN objectives o ON o.id = oe.objective_id
            JOIN objective_status os ON os.objective_id = o.id
            JOIN requirements r ON r.id = o.requirement_id
            JOIN domains d ON d.code = r.domain_code
            JOIN evidence e ON e.id = oe.evidence_id
            ORDER BY d.sort_order, r.id, o.letter, e.title
            """
        ).fetchall()
        for row in rows:
            folder = domain_export_folder(row["domain_order"], row["domain"])
            used = used_by_folder.setdefault(folder, set())
            export_name = generated_evidence_filename(
                row["objective_id"],
                row["title"],
                row["extension"],
                used,
            )
            source = evidence_dir().parent / row["stored_path"]
            archive.write(source, f"{folder}/{export_name}")
            writer.writerow(
                [
                    row["domain"],
                    row["requirement_id"],
                    row["objective_id"],
                    row["status"],
                    row["evidence_id"],
                    row["title"],
                    row["original_filename"],
                    f"{folder}/{export_name}",
                    row["sha256"],
                    row["capture_date"],
                    row["notes"],
                ]
            )
        archive.writestr("manifest.csv", manifest.getvalue())
    return zip_path


def duplicate_to_response_file(path: Path) -> io.BytesIO:
    output = io.BytesIO()
    with path.open("rb") as handle:
        shutil.copyfileobj(handle, output)
    output.seek(0)
    return output
