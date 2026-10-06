"""Deterministic, project-scoped HIPAA package generation."""

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from api import cmmc, ssp
from api.close import fieldwork_ready
from api.database import active_assessment_by_id
from api.renderers import cmmc as cmmc_renderer
from api.renderers.hipaa import render_poam, render_report, validate_snapshot
from api.storage import FileStorage

__all__ = [
    "generate_package",
    "list_packages",
    "render_package",
    "render_poam",
    "render_report",
]

# Each template version is an immutable folder. Changing a template that an issued
# package used means adding a new version here and making it current; the old
# folder stays so earlier packages keep their own review binding.
TEMPLATE_VERSIONS: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "hipaa-v2": (
        "docs/templates/hipaa/v2",
        (
            ("assessment_report", "RainTech_HIPAA_Combined_Assessment_Report_v2.docx"),
            ("poam", "RainTech_HIPAA_POAM_v2.xlsx"),
        ),
    ),
    "cmmc-v1": (
        "docs/templates/cmmc/ssp-v1",
        (("ssp_structure", "structure.json"),),
    ),
}
CURRENT_TEMPLATE_VERSION = "hipaa-v2"
TEMPLATE_ROOT, TEMPLATES = TEMPLATE_VERSIONS[CURRENT_TEMPLATE_VERSION]


# HIPAA versions render one component per template file. The CMMC structure
# file instead drives four rendered components.
RENDERED_COMPONENT_KINDS: dict[str, frozenset[str]] = {
    "cmmc-v1": frozenset({"assessment_report", "ssp", "poam", "evidence_index"}),
}


def package_component_kinds(version: str) -> set[str]:
    if version in RENDERED_COMPONENT_KINDS:
        return set(RENDERED_COMPONENT_KINDS[version])
    return {kind for kind, _ in TEMPLATE_VERSIONS[version][1]}


def package_template_version(declarations: dict[str, Any]) -> str:
    """The current package template for a framework; HIPAA predates the declaration."""
    return str(declarations.get("package_template_version", CURRENT_TEMPLATE_VERSION))


def _cmmc_source(
    c: sqlite3.Connection, project_id: str, assessment: sqlite3.Row, declarations: dict[str, Any]
) -> dict[str, Any]:
    # Imported here: api.main imports this module, and owns the shared rollup.
    from api.main import _derived_status

    approved_ssp = ssp.snapshot_for_package(c, project_id, assessment["id"])
    if approved_ssp is None:
        raise ValueError("An approved System Security Plan is required")
    requirements = []
    for row in c.execute(
        """SELECT record_id, citation, title, work_area FROM framework_records
           WHERE framework_version_id = ? AND parent_id IS NULL ORDER BY sort_order""",
        (assessment["framework_version_id"],),
    ).fetchall():
        requirements.append(
            {
                "record_id": row["record_id"],
                "citation": row["citation"],
                "title": row["title"],
                "domain": row["work_area"],
                "status": _derived_status(c, assessment["id"], row["record_id"]),
                "objectives": [
                    o["record_id"]
                    for o in c.execute(
                        """SELECT record_id FROM framework_records
                           WHERE framework_version_id = ? AND parent_id = ? ORDER BY sort_order""",
                        (assessment["framework_version_id"], row["record_id"]),
                    )
                ],
            }
        )
    findings = []
    for link in c.execute(
        """SELECT rf.record_id, f.id, f.title FROM requirement_findings rf
           JOIN findings f ON f.id = rf.finding_id
           WHERE rf.project_id = ? ORDER BY rf.record_id""",
        (project_id,),
    ).fetchall():
        detail = cmmc.requirement_finding(
            c, project_id, assessment, link["record_id"], _derived_status
        )
        assert detail is not None
        closures = {
            row["corrective_action_id"]: dict(row)
            for row in c.execute("SELECT * FROM poam_closures WHERE finding_id = ?", (link["id"],))
        }
        findings.append(
            {
                "record_id": link["record_id"],
                "finding_id": link["id"],
                "title": link["title"],
                "poam_items": [
                    {
                        **item,
                        "closed_at": closures.get(item["id"], {}).get("closed_at"),
                        "closure_rationale": closures.get(item["id"], {}).get("rationale"),
                    }
                    for item in detail["poam_items"]
                ],
                "history": detail["history"],
            }
        )
    return {
        "score": cmmc.score(c, assessment, declarations["scoring"], _derived_status),
        "requirements": requirements,
        "findings": findings,
        "ssp": approved_ssp,
    }


def template_files(root: Path, version: str) -> list[tuple[str, Path]]:
    if version not in TEMPLATE_VERSIONS:
        raise ValueError(f"Unknown template version: {version}")
    folder, files = TEMPLATE_VERSIONS[version]
    return [(kind, root / folder / filename) for kind, filename in files]


def template_hashes(root: Path, version: str) -> dict[str, str]:
    return {
        kind: sha256(path.read_bytes()).hexdigest() for kind, path in template_files(root, version)
    }


def assert_template_unchanged(connection: sqlite3.Connection, root: Path, version: str) -> None:
    """Refuse to render with a template version whose issued bytes have changed."""
    current = template_hashes(root, version)
    for (manifest_json,) in connection.execute(
        """SELECT p.manifest_json FROM generated_packages p
           JOIN issuance_snapshots i ON i.package_id = p.id AND i.project_id = p.project_id
           WHERE p.template_version = ?""",
        (version,),
    ):
        if json.loads(manifest_json).get("template_hashes") != current:
            raise ValueError(
                f"Template version {version} was used by an issued package and its files "
                "have changed; publish the change as a new template version"
            )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _decision_is_ready(decision: dict[str, Any]) -> bool:
    return decision.get("ready") is True and decision.get("status") == "Ready"


def _rows(
    c: sqlite3.Connection, table: str, where: str, args: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    try:
        return [dict(r) for r in c.execute(f"SELECT * FROM {table} WHERE {where}", args)]
    except sqlite3.OperationalError:
        return []


def _snapshot(
    c: sqlite3.Connection,
    project_id: str,
    assessment_id: str,
    assessment: sqlite3.Row,
) -> tuple[dict[str, Any], str, sqlite3.Row]:
    active_assessment = active_assessment_by_id(c, assessment_id)
    if active_assessment is None or active_assessment["project_id"] != project_id:
        raise ValueError("Assessment is not the active assessment for this project")
    if assessment["id"] != active_assessment["id"] or assessment["project_id"] != project_id:
        raise ValueError("Assessment is not the active assessment for this project")
    active = c.execute(
        "SELECT active_profile_version_id FROM projects WHERE id=?", (project_id,)
    ).fetchone()
    profile = c.execute(
        """
        SELECT pv.*, le.content_revision AS revision_token
        FROM profile_versions pv
        JOIN profile_lifecycle_events le ON le.profile_version_id = pv.id
        WHERE pv.project_id = ? AND le.status = 'Approved'
        ORDER BY le.created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if active and active["active_profile_version_id"]:
        profile = (
            c.execute(
                """
            SELECT pv.*, le.content_revision AS revision_token
            FROM profile_versions pv
            JOIN profile_lifecycle_events le ON le.profile_version_id = pv.id
            WHERE pv.id = ? AND le.status = 'Approved'
            ORDER BY le.created_at DESC
            LIMIT 1
            """,
                (active["active_profile_version_id"],),
            ).fetchone()
            or profile
        )
    if profile is None:
        raise ValueError("An approved Profile lifecycle snapshot is required")
    names = c.execute(
        """SELECT p.name AS project_name, clients.name AS client_name
           FROM projects p JOIN clients ON clients.id = p.client_id
           WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    if names is None:
        raise ValueError("Project and client are required for generation")
    framework = c.execute(
        "SELECT * FROM framework_versions WHERE id=?", (assessment["framework_version_id"],)
    ).fetchone()
    framework_row = dict(framework) if framework else {}
    declarations = json.loads(framework_row.get("declarations_json", "{}"))
    records = _rows(
        c, "framework_records", "framework_version_id=?", (assessment["framework_version_id"],)
    )
    determinations = {
        r["record_id"]: r for r in _rows(c, "determinations", "assessment_id=?", (assessment_id,))
    }
    findings = _rows(c, "findings", "project_id=?", (project_id,))
    actions = _rows(c, "corrective_actions", "project_id=?", (project_id,))
    for row in records:
        d = determinations.get(row.get("record_id"))
        row.update(d or {})
        row["text"] = row.get("text") or row.get("regulation_text") or row.get("title")
        if d and d.get("na_rationale"):
            row["rationale"] = d["na_rationale"]
        reconciliation = next(
            iter(
                _rows(
                    c,
                    "not_met_reconciliations",
                    "assessment_id=? AND record_id=?",
                    (assessment_id, row.get("record_id")),
                )
            ),
            None,
        )
        f = next(
            (
                x
                for x in findings
                if reconciliation and x.get("id") == reconciliation.get("finding_id")
            ),
            None,
        )
        a = next(
            (
                x
                for x in actions
                if reconciliation and x.get("id") == reconciliation.get("corrective_action_id")
            ),
            None,
        )
        if f:
            row["finding_id"] = f["id"]
            row["finding_title"] = f["title"]
            row["finding_description"] = f["description"]
        if a:
            row["action_id"] = a["id"]
            row["corrective_action_id"] = a["id"]
            row["action_title"] = a["title"]
            row["action_description"] = a["description"]
            row["poam_status"] = a["status"]
    source: dict[str, Any] = {
        "snapshot_id": str(uuid4()),
        "template_version": package_template_version(declarations),
        "framework": {
            "id": assessment["framework_version_id"],
            "title": framework_row.get("name"),
            "version": assessment["framework_version_id"],
            "declarations": declarations,
        },
        "assessment": {**dict(assessment), "project_name": names["project_name"]},
        "profile": {
            **dict(profile),
            "snapshot_id": profile["id"],
            "client_name": names["client_name"],
        },
        "records": records,
        "risks": _rows(c, "risks", "project_id=?", (project_id,)),
        "profile_values": _rows(
            c, "profile_field_values", "profile_version_id=?", (profile["id"],)
        ),
        "determinations": list(determinations.values()),
        "findings": findings,
        "corrective_actions": actions,
        "actions": actions,
        "reconciliations": _rows(c, "not_met_reconciliations", "project_id=?", (project_id,)),
        "sra_scope": _rows(c, "sra_scope_reviews", "project_id=?", (project_id,)),
        "evidence_versions": _rows(c, "evidence_versions", "project_id=?", (project_id,)),
        "readiness": fieldwork_ready(c, project_id, assessment_id),
    }
    if declarations.get("scoring"):
        source["cmmc"] = _cmmc_source(c, project_id, assessment, declarations)
        errors = [] if source["cmmc"]["score"]["complete"] else ["CMMC score is not complete"]
    else:
        errors = validate_snapshot(source)
    if errors:
        raise ValueError("Snapshot is not renderable: " + "; ".join(errors))
    encoded = json.dumps(source, sort_keys=True, separators=(",", ":"))
    return source, sha256(encoded.encode()).hexdigest(), profile


def generate_package(
    connection: sqlite3.Connection,
    storage: FileStorage,
    root: Path,
    project_id: str,
    assessment_id: str,
    staging_root: Path | None = None,
) -> dict[str, Any]:
    active_assessment = active_assessment_by_id(connection, assessment_id)
    if active_assessment is None or active_assessment["project_id"] != project_id:
        raise ValueError("Assessment is not the active assessment for this project")
    assessment = connection.execute(
        """
        SELECT assessments.*, assessment_revisions.revision_number
        FROM assessments
        JOIN assessment_revisions
          ON assessment_revisions.assessment_id = assessments.id
         AND assessment_revisions.project_id = assessments.project_id
        WHERE assessments.id = ? AND assessments.project_id = ?
        """,
        (assessment_id, project_id),
    ).fetchone()
    if assessment is None:
        raise ValueError("Assessment does not belong to project")
    if not _decision_is_ready(fieldwork_ready(connection, project_id, assessment_id)):
        raise ValueError("Assessment is not ready for generation")
    source, source_hash, profile = _snapshot(connection, project_id, assessment_id, assessment)
    snapshot_id = source["snapshot_id"]
    connection.execute(
        "INSERT INTO source_snapshots VALUES (?,?,?,?,?,?,?,?,?)",
        (
            snapshot_id,
            project_id,
            assessment_id,
            assessment["revision_number"],
            profile["id"],
            profile["revision_token"],
            json.dumps(source, sort_keys=True, separators=(",", ":")),
            source_hash,
            _now(),
        ),
    )
    return render_package(
        connection,
        storage,
        root,
        project_id,
        assessment_id,
        source,
        source_hash,
        "fieldwork_ready_for_generation",
        staging_root,
    )


def render_package(
    connection: sqlite3.Connection,
    storage: FileStorage,
    root: Path,
    project_id: str,
    assessment_id: str,
    source: dict[str, Any],
    source_hash: str,
    target: str,
    staging_root: Path | None = None,
) -> dict[str, Any]:
    """Render and promote a complete package from an already stored source snapshot."""
    snapshot_id, attempt_id, package_id, created = (
        source["snapshot_id"],
        str(uuid4()),
        str(uuid4()),
        _now(),
    )
    connection.execute(
        "INSERT INTO generation_attempts VALUES (?,?,?,?,?,?,?,?,?)",
        (
            attempt_id,
            project_id,
            assessment_id,
            target,
            "staged",
            snapshot_id,
            None,
            created,
            None,
        ),
    )
    version = package_template_version(source["framework"]["declarations"])
    assert_template_unchanged(connection, root, version)
    # The stored snapshot is immutable; render it with the version actually used.
    rendered_source = {**source, "template_version": version}
    staged = []
    promoted = []
    try:
        components = []
        render_staging = staging_root or root / "data" / "generation-staging"
        render_staging.mkdir(parents=True, exist_ok=True)
        rendered: list[tuple[str, str, bytes]] = []
        if "cmmc" in rendered_source:
            rendered = cmmc_renderer.render_package(rendered_source)
        for kind, template in [] if rendered else template_files(root, version):
            filename = template.name
            component_id = str(uuid4())
            content = template.read_bytes()
            if kind == "assessment_report":
                out = render_staging / f"{component_id}-{filename}"
                render_report(template, out, rendered_source)
                content = out.read_bytes()
                out.unlink(missing_ok=True)
            elif kind == "poam":
                out = render_staging / f"{component_id}-{filename}"
                render_poam(template, out, rendered_source)
                content = out.read_bytes()
                out.unlink(missing_ok=True)
            staged_path, final_path = storage.stage(project_id, component_id, filename, content)
            staged.append((staged_path, final_path))
            components.append(
                {
                    "id": component_id,
                    "kind": kind,
                    "filename": filename,
                    "path": final_path,
                    "sha256": sha256(content).hexdigest(),
                    "bytes": len(content),
                }
            )
        for kind, filename, content in rendered:
            component_id = str(uuid4())
            staged_path, final_path = storage.stage(project_id, component_id, filename, content)
            staged.append((staged_path, final_path))
            components.append(
                {
                    "id": component_id,
                    "kind": kind,
                    "filename": filename,
                    "path": final_path,
                    "sha256": sha256(content).hexdigest(),
                    "bytes": len(content),
                }
            )
        manifest = {
            "project_id": project_id,
            "assessment_id": assessment_id,
            "source_snapshot_sha256": source_hash,
            "template_version": version,
            "template_hashes": template_hashes(root, version),
            "components": components,
        }
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        connection.execute(
            "INSERT INTO generated_packages VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                package_id,
                project_id,
                assessment_id,
                attempt_id,
                snapshot_id,
                version,
                "staged",
                manifest_json,
                sha256(manifest_json.encode()).hexdigest(),
                created,
            ),
        )
        for item in components:
            connection.execute(
                "INSERT INTO generated_components VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    item["id"],
                    project_id,
                    package_id,
                    item["kind"],
                    item["filename"],
                    item["path"],
                    item["sha256"],
                    item["bytes"],
                    created,
                ),
            )
        for staged_path, final_path in staged:
            storage.promote(staged_path, final_path)
            promoted.append(final_path)
        connection.execute(
            "UPDATE generated_packages SET state='promoted' WHERE id=?", (package_id,)
        )
        connection.execute(
            "UPDATE generation_attempts SET state='promoted',completed_at=? WHERE id=?",
            (_now(), attempt_id),
        )
        return {
            "id": package_id,
            "project_id": project_id,
            "assessment_id": assessment_id,
            "state": "promoted",
            "manifest": manifest,
        }
    except Exception as exc:
        for path in [p for p, _ in staged] + promoted:
            storage.delete(path)
        connection.execute(
            "UPDATE generation_attempts SET state='failed',error=?,completed_at=? WHERE id=?",
            (str(exc), _now(), attempt_id),
        )
        raise


def list_packages(connection: sqlite3.Connection, project_id: str) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in connection.execute(
            "SELECT * FROM generated_packages WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        )
    ]
