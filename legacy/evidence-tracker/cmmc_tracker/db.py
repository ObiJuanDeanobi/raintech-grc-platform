from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from .paths import SEED_PATH, data_dir, db_path, evidence_dir, exports_dir


STATUSES = ["Not Captured", "Captured", "Escalating"]


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path(), factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path=None) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    evidence_dir().mkdir(parents=True, exist_ok=True)
    exports_dir().mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.executescript(PLATFORM_SCHEMA)
        seed_database(conn)
        migrate_requirement_guide_sections(conn)
        migrate_statuses(conn)
        seed_platform_templates(conn)


def seed_database(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM objectives").fetchone()[0]:
        return
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    conn.executemany(
        "INSERT INTO domains(code, name, sort_order) VALUES(:code, :name, :sort_order)",
        seed["domains"],
    )
    conn.executemany(
        """
        INSERT INTO requirements(id, domain_code, name, text, potential_methods, discussion, further_discussion)
        VALUES(:id, :domain_code, :name, :text, :potential_methods, :discussion, :further_discussion)
        """,
        seed["requirements"],
    )
    conn.executemany(
        """
        INSERT INTO objectives(id, requirement_id, letter, text, evidence_examples)
        VALUES(:id, :requirement_id, :letter, :text, :evidence_examples)
        """,
        [
            {
                **objective,
                "evidence_examples": json.dumps(objective["evidence_examples"]),
            }
            for objective in seed["objectives"]
        ],
    )
    now = datetime.now(UTC).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT INTO objective_status(objective_id, status, notes, updated_at) VALUES(?, ?, ?, ?)",
        [(objective["id"], "Not Captured", "", now) for objective in seed["objectives"]],
    )
    conn.execute(
        "INSERT INTO settings(id, company_id, company_name) VALUES(1, 'ID', 'COMPANY')"
    )


def migrate_statuses(conn: sqlite3.Connection) -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE objective_status
        SET status = CASE
            WHEN objective_id IN (SELECT DISTINCT objective_id FROM objective_evidence) THEN 'Captured'
            ELSE 'Not Captured'
        END,
        updated_at = ?
        WHERE status NOT IN ('Not Captured', 'Captured', 'Escalating')
        """,
        (now,),
    )


def migrate_requirement_guide_sections(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(requirements)").fetchall()
    }
    for column in ("potential_methods", "discussion", "further_discussion"):
        if column not in existing:
            conn.execute(f"ALTER TABLE requirements ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    conn.executemany(
        """
        UPDATE requirements
        SET potential_methods = :potential_methods,
            discussion = :discussion,
            further_discussion = :further_discussion
        WHERE id = :id
        """,
        seed["requirements"],
    )


SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    domain_code TEXT NOT NULL REFERENCES domains(code),
    name TEXT NOT NULL,
    text TEXT NOT NULL,
    potential_methods TEXT NOT NULL DEFAULT '',
    discussion TEXT NOT NULL DEFAULT '',
    further_discussion TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS objectives (
    id TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(id),
    letter TEXT NOT NULL,
    text TEXT NOT NULL,
    evidence_examples TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objective_status (
    objective_id TEXT PRIMARY KEY REFERENCES objectives(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'Not Captured',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    extension TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    capture_date TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objective_evidence (
    objective_id TEXT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    PRIMARY KEY(objective_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    company_id TEXT NOT NULL DEFAULT 'ID',
    company_name TEXT NOT NULL DEFAULT 'COMPANY'
);

"""


PLATFORM_SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cage_code TEXT NOT NULL DEFAULT '',
    uei_number TEXT NOT NULL DEFAULT '',
    primary_contact_name TEXT NOT NULL DEFAULT '',
    primary_contact_email TEXT NOT NULL DEFAULT '',
    primary_contact_phone TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    portal_enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS implementation_profiles (
    client_id TEXT PRIMARY KEY REFERENCES clients(id) ON DELETE CASCADE,
    legal_name TEXT NOT NULL DEFAULT '',
    system_name TEXT NOT NULL DEFAULT '',
    environment_shape TEXT NOT NULL DEFAULT '',
    required_cloud TEXT NOT NULL DEFAULT '',
    current_cloud TEXT NOT NULL DEFAULT '',
    cui_type TEXT NOT NULL DEFAULT '',
    cui_flow TEXT NOT NULL DEFAULT '',
    cui_location TEXT NOT NULL DEFAULT '',
    cui_users INTEGER,
    total_employees INTEGER,
    total_endpoints INTEGER,
    endpoint_management TEXT NOT NULL DEFAULT '',
    mfa_status TEXT NOT NULL DEFAULT '',
    logging_status TEXT NOT NULL DEFAULT '',
    encryption_status TEXT NOT NULL DEFAULT '',
    external_access TEXT NOT NULL DEFAULT '',
    external_service_providers TEXT NOT NULL DEFAULT '',
    timeline TEXT NOT NULL DEFAULT '',
    internal_owner TEXT NOT NULL DEFAULT '',
    ongoing_support TEXT NOT NULL DEFAULT '',
    quote_answers_json TEXT NOT NULL DEFAULT '{}',
    profile_json TEXT NOT NULL DEFAULT '{}',
    questionnaire_complete INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quote_records (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    readiness_score INTEGER NOT NULL DEFAULT 0,
    package_name TEXT NOT NULL,
    quote_range TEXT NOT NULL,
    confidence TEXT NOT NULL,
    assumptions TEXT NOT NULL DEFAULT '',
    answers_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    framework TEXT NOT NULL DEFAULT 'CMMC Level 2',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessment_results (
    id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    objective_id TEXT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'not_assessed',
    notes TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE(assessment_id, objective_id)
);

CREATE TABLE IF NOT EXISTS assessment_evidence (
    result_id TEXT NOT NULL REFERENCES assessment_results(id) ON DELETE CASCADE,
    evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    linked_at TEXT NOT NULL,
    PRIMARY KEY(result_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS poam_items (
    id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    objective_id TEXT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    gap TEXT NOT NULL DEFAULT '',
    remediation TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_templates (
    id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_documents (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    assessment_id TEXT REFERENCES assessments(id) ON DELETE SET NULL,
    doc_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    filename TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


DEFAULT_DOCUMENT_TEMPLATES = [
    {
        "id": "ssp",
        "doc_type": "ssp",
        "title": "System Security Plan",
        "body": """# System Security Plan - {{client_name}}

## System Identification
System Name: {{system_name}}
Environment: {{required_cloud}}
CUI Environment Shape: {{environment_shape}}

## CUI Scope
{{cui_summary}}

## Operating Environment
{{environment_summary}}

## Control Implementation Summary
{{control_summary}}

## Evidence Capture Status
{{evidence_summary}}
""",
    },
    {
        "id": "access-control-policy",
        "doc_type": "policy",
        "title": "Access Control Policy",
        "body": """# Access Control Policy - {{client_name}}

This policy governs access to the {{system_name}} CUI environment.

## Access Scope
{{cui_summary}}

## Required Controls
- MFA is required for privileged, remote, and CUI access.
- Access is limited to authorized CUI users.
- External access must follow the approved CUI access model.
""",
    },
    {
        "id": "incident-response-procedure",
        "doc_type": "procedure",
        "title": "Incident Response Procedure",
        "body": """# Incident Response Procedure - {{client_name}}

## Purpose
Define the process for responding to security incidents affecting the CUI environment.

## Reporting Context
The environment profile identifies {{required_cloud}} as the target environment and {{external_access}} as the external access model.

## Evidence Needed
Maintain incident response plan approval, test records, training records, and incident tickets.
""",
    },
    {
        "id": "cui-flow-diagram-notes",
        "doc_type": "diagram",
        "title": "CUI Flow Diagram Notes",
        "body": """# CUI Flow Diagram Notes - {{client_name}}

Sources, entry points, repositories, endpoints, blocked paths, and external access should be diagrammed from this profile:

{{cui_summary}}
""",
    },
]


def seed_platform_templates(conn: sqlite3.Connection) -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    for template in DEFAULT_DOCUMENT_TEMPLATES:
        conn.execute(
            """
            INSERT OR IGNORE INTO document_templates(id, doc_type, title, body, created_at, updated_at)
            VALUES(:id, :doc_type, :title, :body, :created_at, :updated_at)
            """,
            {**template, "created_at": now, "updated_at": now},
        )
