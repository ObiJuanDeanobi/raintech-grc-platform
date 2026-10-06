"""CMMC System Security Plan: generate, version, approve, export (GitHub issue #107).

The structure follows the public NIST SP 800-171 CUI SSP template, pinned as
``docs/templates/cmmc/ssp-v1/structure.json``. An SSP is generated only from an
approved Profile and an assessment whose 110 requirements all derive Met or
Not Met. Edits append versions; approval freezes the document. DOCX exports are
delivery copies and are never the system of record.
"""

# ruff: noqa: E501

import json
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.sax.saxutils import escape

from fastapi import HTTPException

TEMPLATE_VERSION = "cmmc-ssp-v1"
TEMPLATE_PATH = Path("docs/templates/cmmc/ssp-v1/structure.json")
TEMPLATE_SHA256 = "f55f0006b8f09a37a94e250a8663a99a3878e7ac328c21af84a3687fe21dab6d"
ENVIRONMENT_ITEMS = ("environment", "scope_item", "location", "external_service", "person_role")

Derive = Callable[[Any, str, str], str]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_template(root: Path) -> dict[str, Any]:
    raw = (root / TEMPLATE_PATH).read_bytes()
    if sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise HTTPException(409, "The SSP template changed; approve a new template version first")
    return dict(json.loads(raw))


def _approved_profile(connection: Any, project_id: str) -> Any:
    return connection.execute(
        """SELECT pv.id FROM profile_versions pv
           JOIN profile_lifecycle_events le ON le.profile_version_id = pv.id
           WHERE pv.project_id = ? AND le.status = 'Approved'
           ORDER BY le.created_at DESC LIMIT 1""",
        (project_id,),
    ).fetchone()


def _profile(connection: Any, profile_version_id: str) -> tuple[list[dict[str, str]], list[Any]]:
    fields = [
        {"section": r["section"], "label": r["label"], "value": r["value"]}
        for r in connection.execute(
            """SELECT section, label, value FROM profile_field_values
               WHERE profile_version_id = ? AND profile_item_id IS NULL
               ORDER BY section, sort_order""",
            (profile_version_id,),
        )
    ]
    items = []
    for item in connection.execute(
        "SELECT * FROM profile_items WHERE profile_version_id = ? ORDER BY sort_order",
        (profile_version_id,),
    ):
        if item["item_type"] not in ENVIRONMENT_ITEMS:
            continue
        items.append(
            {
                "item_type": item["item_type"],
                "key": item["client_key"],
                "fields": [
                    {"label": r["label"], "value": r["value"]}
                    for r in connection.execute(
                        """SELECT label, value FROM profile_field_values
                           WHERE profile_item_id = ? ORDER BY sort_order""",
                        (item["id"],),
                    )
                ],
            }
        )
    return fields, items


def _draft_implementation(connection: Any, assessment_id: str, requirement: Any) -> str:
    """Draft from the assessor's own notes and observations; never invented text."""
    lines = []
    note = connection.execute(
        "SELECT note FROM record_notes WHERE assessment_id = ? AND record_id = ?",
        (assessment_id, requirement["record_id"]),
    ).fetchone()
    if note and note["note"].strip():
        lines.append(note["note"].strip())
    for objective in connection.execute(
        """SELECT r.citation, COALESCE(n.note, '') AS note,
                  COALESCE(d.interview_observation, '') AS observation
           FROM framework_records r
           JOIN assessments a ON a.framework_version_id = r.framework_version_id
           LEFT JOIN record_notes n ON n.assessment_id = a.id AND n.record_id = r.record_id
           LEFT JOIN determinations d ON d.assessment_id = a.id AND d.record_id = r.record_id
           WHERE a.id = ? AND r.parent_id = ? ORDER BY r.sort_order""",
        (assessment_id, requirement["record_id"]),
    ):
        text = " ".join(
            p for p in (objective["note"].strip(), objective["observation"].strip()) if p
        )
        if text:
            lines.append(f"{objective['citation']}: {text}")
    return "\n".join(lines)


def generate(
    connection: Any,
    root: Path,
    project_id: str,
    assessment: Any,
    actor_id: str,
    derive: Derive,
) -> dict[str, Any]:
    template = load_template(root)
    blockers = []
    profile = _approved_profile(connection, project_id)
    if profile is None:
        blockers.append("Approve a Project Profile version first.")
    requirements = list(
        connection.execute(
            """SELECT record_id, citation, title, regulation_text, work_area FROM framework_records
               WHERE framework_version_id = ? AND parent_id IS NULL ORDER BY sort_order""",
            (assessment["framework_version_id"],),
        )
    )
    statuses = {
        r["record_id"]: derive(connection, assessment["id"], r["record_id"]) for r in requirements
    }
    unresolved = [
        rid for rid, status in statuses.items() if status not in template["requirement_statuses"]
    ]
    if unresolved:
        blockers.append(
            f"{len(unresolved)} requirement(s) are not Met or Not Met: "
            + ", ".join(unresolved[:10])
        )
    if blockers:
        raise HTTPException(409, {"blockers": blockers})
    fields, items = _profile(connection, profile["id"])
    names = connection.execute(
        """SELECT p.name AS project_name, c.name AS client_name
           FROM projects p JOIN clients c ON c.id = p.client_id WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    source_requirements = []
    for requirement in requirements:
        poam = [
            row["title"]
            for row in connection.execute(
                """SELECT a.title FROM corrective_actions a
                   JOIN requirement_findings f ON f.finding_id = a.finding_id
                   WHERE f.project_id = ? AND f.record_id = ? ORDER BY a.created_at""",
                (project_id, requirement["record_id"]),
            )
        ]
        source_requirements.append(
            {
                "record_id": requirement["record_id"],
                "citation": requirement["citation"],
                "title": requirement["title"],
                "text": requirement["regulation_text"],
                "domain": requirement["work_area"],
                "determination": statuses[requirement["record_id"]],
                "status": template["requirement_statuses"][statuses[requirement["record_id"]]],
                "poam_items": poam,
                "drafted_implementation": _draft_implementation(
                    connection, assessment["id"], requirement
                ),
            }
        )
    source = {
        "project_id": project_id,
        "assessment_id": assessment["id"],
        "framework_version_id": assessment["framework_version_id"],
        "profile_version_id": profile["id"],
        "client_name": names["client_name"],
        "project_name": names["project_name"],
        "profile_fields": fields,
        "environment_items": items,
        "requirements": source_requirements,
    }
    content = {
        "system_description": "",
        "environment_narrative": "",
        "requirements": {
            r["record_id"]: {"implementation": r["drafted_implementation"]}
            for r in source_requirements
        },
    }
    ssp_id, created = str(uuid4()), _now()
    source_json = _canonical(source)
    connection.execute(
        """INSERT INTO ssp_documents(
               id, project_id, assessment_id, template_version, template_sha256,
               source_json, source_sha256, created_by, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ssp_id,
            project_id,
            assessment["id"],
            TEMPLATE_VERSION,
            TEMPLATE_SHA256,
            source_json,
            sha256(source_json.encode()).hexdigest(),
            actor_id,
            created,
        ),
    )
    _add_version(
        connection, ssp_id, project_id, content, "Generated from the assessment.", actor_id
    )
    return view(connection, project_id, ssp_id)


def _add_version(
    connection: Any, ssp_id: str, project_id: str, content: dict[str, Any], note: str, actor_id: str
) -> None:
    number = connection.execute(
        "SELECT COALESCE(MAX(version_number), 0) + 1 FROM ssp_versions WHERE ssp_id = ?", (ssp_id,)
    ).fetchone()[0]
    content_json = _canonical(content)
    connection.execute(
        """INSERT INTO ssp_versions(
               id, ssp_id, project_id, version_number, content_json, content_sha256,
               note, created_by, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid4()),
            ssp_id,
            project_id,
            number,
            content_json,
            sha256(content_json.encode()).hexdigest(),
            note,
            actor_id,
            _now(),
        ),
    )


def document_or_404(connection: Any, project_id: str, ssp_id: str) -> Any:
    row = connection.execute(
        "SELECT * FROM ssp_documents WHERE id = ? AND project_id = ?", (ssp_id, project_id)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "SSP not found")
    return row


def _versions(connection: Any, ssp_id: str) -> list[dict[str, Any]]:
    return [
        {**dict(row), "content": json.loads(row["content_json"])}
        for row in connection.execute(
            """SELECT id, version_number, content_json, content_sha256, note, created_by, created_at
               FROM ssp_versions WHERE ssp_id = ? ORDER BY version_number""",
            (ssp_id,),
        )
    ]


def _missing(source: dict[str, Any], content: dict[str, Any]) -> list[str]:
    missing = [
        key for key in ("system_description", "environment_narrative") if not content[key].strip()
    ]
    missing += [
        r["record_id"]
        for r in source["requirements"]
        if not content["requirements"][r["record_id"]]["implementation"].strip()
    ]
    return missing


def view(connection: Any, project_id: str, ssp_id: str) -> dict[str, Any]:
    document = document_or_404(connection, project_id, ssp_id)
    versions = _versions(connection, ssp_id)
    approval = connection.execute(
        "SELECT * FROM ssp_approvals WHERE ssp_id = ?", (ssp_id,)
    ).fetchone()
    source = json.loads(document["source_json"])
    latest = versions[-1]
    for version in versions[:-1]:
        version.pop("content")
    return {
        "id": ssp_id,
        "assessment_id": document["assessment_id"],
        "template_version": document["template_version"],
        "template_sha256": document["template_sha256"],
        "source_sha256": document["source_sha256"],
        "source": source,
        "versions": versions,
        "latest": latest,
        "missing_for_approval": _missing(source, latest["content"]),
        "approval": dict(approval) if approval else None,
    }


def latest_for_project(
    connection: Any, project_id: str, assessment_id: str
) -> dict[str, Any] | None:
    row = connection.execute(
        """SELECT id FROM ssp_documents WHERE project_id = ? AND assessment_id = ?
           ORDER BY created_at DESC, rowid DESC LIMIT 1""",
        (project_id, assessment_id),
    ).fetchone()
    return view(connection, project_id, row["id"]) if row else None


def edit(
    connection: Any, project_id: str, ssp_id: str, changes: dict[str, Any], note: str, actor_id: str
) -> dict[str, Any]:
    document = document_or_404(connection, project_id, ssp_id)
    if connection.execute("SELECT 1 FROM ssp_approvals WHERE ssp_id = ?", (ssp_id,)).fetchone():
        raise HTTPException(409, "This SSP is approved and frozen")
    content = _versions(connection, ssp_id)[-1]["content"]
    for key in ("system_description", "environment_narrative"):
        if key in changes:
            content[key] = str(changes[key])
    known = {r["record_id"] for r in json.loads(document["source_json"])["requirements"]}
    for record_id, text in dict(changes.get("requirements", {})).items():
        if record_id not in known:
            raise HTTPException(422, f"Unknown requirement: {record_id}")
        content["requirements"][record_id]["implementation"] = str(text)
    _add_version(connection, ssp_id, project_id, content, note.strip() or "Edited.", actor_id)
    return view(connection, project_id, ssp_id)


def approve(connection: Any, project_id: str, ssp_id: str, actor_id: str) -> dict[str, Any]:
    current = view(connection, project_id, ssp_id)
    if current["approval"]:
        raise HTTPException(409, "This SSP is already approved")
    if current["missing_for_approval"]:
        raise HTTPException(
            409,
            {
                "blockers": [
                    "Complete before approval: " + ", ".join(current["missing_for_approval"])
                ]
            },
        )
    connection.execute(
        """INSERT INTO ssp_approvals(id, ssp_id, ssp_version_id, project_id, approver_id, approved_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid4()), ssp_id, current["latest"]["id"], project_id, actor_id, _now()),
    )
    return view(connection, project_id, ssp_id)


def _paragraph(text: str, style: str | None = None) -> str:
    props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    runs = "".join(
        f'<w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r>'
        + ("<w:r><w:br/></w:r>" if i < len(text.split("\n")) - 1 else "")
        for i, line in enumerate(text.split("\n"))
    )
    return f"<w:p>{props}{runs}</w:p>"


def render_docx(connection: Any, project_id: str, ssp_id: str, version_number: int) -> bytes:
    """Deterministic DOCX delivery copy of one SSP version."""
    current = view(connection, project_id, ssp_id)
    versions = _versions(connection, ssp_id)
    chosen = next((v for v in versions if v["version_number"] == version_number), None)
    if chosen is None:
        raise HTTPException(404, "SSP version not found")
    source, content = current["source"], chosen["content"]
    approval = current["approval"]
    body = [
        _paragraph("System Security Plan", "Title"),
        _paragraph(f"{source['client_name']} · {source['project_name']}"),
        _paragraph(
            f"Version {version_number} · source {current['source_sha256'][:16]} · "
            f"template {current['template_version']}"
            + (
                f" · approved {approval['approved_at'][:10]}"
                if approval and approval["ssp_version_id"] == chosen["id"]
                else " · NOT APPROVED"
            )
        ),
        _paragraph("1. System Identification", "Heading1"),
        _paragraph(content["system_description"] or "[Not yet written]"),
    ]
    body += [_paragraph(f"{f['label']}: {f['value']}") for f in source["profile_fields"]]
    body.append(_paragraph("2. System Environment", "Heading1"))
    body.append(_paragraph(content["environment_narrative"] or "[Not yet written]"))
    for item in source["environment_items"]:
        details = "; ".join(f"{f['label']}: {f['value']}" for f in item["fields"])
        body.append(_paragraph(f"{item['item_type'].replace('_', ' ')} {item['key']}: {details}"))
    body.append(_paragraph("3. Requirements", "Heading1"))
    domain = None
    for requirement in source["requirements"]:
        if requirement["domain"] != domain:
            domain = requirement["domain"]
            body.append(_paragraph(domain, "Heading2"))
        body.append(_paragraph(f"{requirement['citation']} {requirement['title']}", "Heading3"))
        body.append(_paragraph(requirement["text"]))
        body.append(_paragraph(f"Status: {requirement['status']}"))
        implementation = content["requirements"][requirement["record_id"]]["implementation"]
        body.append(_paragraph(implementation or "[Not yet written]"))
        for item in requirement["poam_items"]:
            body.append(_paragraph(f"POA&M: {item}"))
    body.append(_paragraph("4. Record of Changes", "Heading1"))
    for version in versions:
        if version["version_number"] <= version_number:
            body.append(
                _paragraph(
                    f"{version['created_at'][:10]} · v{version['version_number']} · {version['note']}"
                )
            )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}</w:body></w:document>"
    )
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"
        ),
        "word/document.xml": document,
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            archive.writestr(info, data)
    return buffer.getvalue()
