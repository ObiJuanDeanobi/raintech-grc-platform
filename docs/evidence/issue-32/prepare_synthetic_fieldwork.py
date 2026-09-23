#!/usr/bin/env python3
"""Prepare the designated synthetic Issue 32 project through production HTTP APIs.

This script is deliberately pinned to one local packaged instance, project,
Profile draft, and assessment. It does not access SQLite or prompt answers.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:18433"
PROJECT_ID = "03c65d61-164d-45ef-80f2-151658740a58"
PROJECT_NAME = "HIPAA Browser Pilot"
PROFILE_VERSION_ID = "53b743cf-4ef1-470b-9ad0-30a2a479b575"
ASSESSMENT_ID = "770e50b6-dcff-4eed-aee0-babc8220f379"
REMEDIATION_RECORD_ID = "164.308(a)(1)(ii)(B)"
REVIEWER = "Synthetic Acceptance Reviewer"
MET_OBSERVATION_PREFIX = (
    "Synthetic Issue 32 walkthrough observation; test data only; no client facts. "
)
NOT_MET_OBSERVATION = (
    "Synthetic Issue 32 remediation scenario; test data only; no client facts."
)
RISK_TITLE = "Synthetic Issue 32 risk scenario"
FINDING_TITLE = "Synthetic Issue 32 finding: access review"
ACTION_TITLE = "Synthetic Issue 32 action: document review cadence"


class SetupError(RuntimeError):
    pass


def request_json(method: str, path: str, payload: object | None = None) -> object:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError) as error:
        detail = ""
        if isinstance(error, HTTPError):
            detail = error.read().decode("utf-8", errors="replace")[:1000]
        raise SetupError(f"{method} {path} failed: {error}; {detail}") from error
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise SetupError(f"{method} {path} returned invalid JSON") from error


def get(path: str) -> dict:
    value = request_json("GET", path)
    if not isinstance(value, dict):
        raise SetupError(f"GET {path} did not return an object")
    return value


def send(method: str, path: str, payload: object | None = None) -> dict:
    value = request_json(method, path, payload)
    if not isinstance(value, dict):
        raise SetupError(f"{method} {path} did not return an object")
    return value


def field_value(
    section: str, key: str, label: str, value: str, timestamp: str
) -> dict[str, str]:
    return {
        "section": section,
        "field_key": key,
        "label": label,
        "value": value,
        "source": "Synthetic Issue 32 acceptance setup",
        "reviewer": REVIEWER,
        "last_reviewed_at": timestamp,
    }


def normalize_value(value: dict) -> dict[str, str]:
    return {
        key: str(value[key])
        for key in (
            "section",
            "field_key",
            "label",
            "value",
            "source",
            "reviewer",
            "last_reviewed_at",
        )
    }


def ensure_profile() -> None:
    overview = get(f"/api/projects/{PROJECT_ID}/profile")
    if overview.get("project_id") != PROJECT_ID:
        raise SetupError("Project identity check failed")
    version = get(f"/api/projects/{PROJECT_ID}/profile/versions/{PROFILE_VERSION_ID}")
    if version.get("project_id") != PROJECT_ID or version.get("version_number") != 2:
        raise SetupError("Pinned Profile version is not Version 2 of the target project")

    # Keep existing values, including the project name, and keep any items not
    # owned by this deterministic synthetic setup.
    values = [normalize_value(value) for value in version.get("values", [])]
    current_project_name = next(
        (
            value["value"]
            for value in version.get("values", [])
            if value.get("section") == "project_metadata"
            and value.get("field_key") == "project_name"
        ),
        None,
    )
    if current_project_name != PROJECT_NAME:
        raise SetupError("Project name Profile value changed; refusing to replace it")

    original_items = version.get("items", [])
    client_key_by_id = {
        item["id"]: item["client_key"]
        for item in original_items
        if item.get("item_type") == "environment"
    }
    items: list[dict] = []
    for item in original_items:
        items.append(
            {
                "client_key": item["client_key"],
                "item_type": item["item_type"],
                "environment_item_key": client_key_by_id.get(
                    item.get("environment_item_id")
                ),
                "values": [normalize_value(value) for value in item.get("values", [])],
            }
        )

    stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    generated_items: list[dict] = [
        {
            "client_key": "issue32-synthetic-environment",
            "item_type": "environment",
            "environment_item_key": None,
            "values": [
                field_value("environments", "name", "Name", "Synthetic test environment", stamp),
                field_value(
                    "environments", "environment_type", "Environment type", "cloud", stamp
                ),
            ],
        },
        {
            "client_key": "issue32-synthetic-scope",
            "item_type": "scope_item",
            "environment_item_key": "issue32-synthetic-environment",
            "values": [
                field_value(
                    "scope_items", "name", "Name", "Synthetic test workstation", stamp
                ),
                field_value(
                    "scope_items",
                    "description",
                    "Description",
                    "Synthetic inventory for local acceptance only",
                    stamp,
                ),
            ],
        },
        {
            "client_key": "issue32-synthetic-location",
            "item_type": "location",
            "environment_item_key": None,
            "values": [
                field_value(
                    "locations", "name", "Name", "Synthetic test location", stamp
                )
            ],
        },
        {
            "client_key": "issue32-synthetic-vendor",
            "item_type": "external_service",
            "environment_item_key": None,
            "values": [
                field_value(
                    "external_services", "name", "Name", "Synthetic test service", stamp
                )
            ],
        },
        {
            "client_key": "issue32-synthetic-process",
            "item_type": "business_process",
            "environment_item_key": None,
            "values": [
                field_value(
                    "business_processes",
                    "name",
                    "Name",
                    "Synthetic test intake process",
                    stamp,
                )
            ],
        },
    ]

    # Upsert only the fixed synthetic keys. Existing unrelated Profile records
    # remain in the replacement payload unchanged.
    generated_by_key = {item["client_key"]: item for item in generated_items}
    items = [item for item in items if item["client_key"] not in generated_by_key]
    items.extend(generated_items)

    status = version.get("status")
    version_path = f"/api/projects/{PROJECT_ID}/profile/versions/{PROFILE_VERSION_ID}"
    if status == "Draft":
        version = send(
            "PUT",
            version_path,
            {
                "expected_revision": version["content_revision"],
                "values": values,
                "items": items,
            },
        )
        status = version.get("status")
    elif status not in {"Reviewed", "Approved"}:
        raise SetupError(f"Unexpected pinned Profile status: {status}")

    if status in {"Draft", "Reviewed"}:
        for next_status in (
            ["Reviewed", "Approved"] if status == "Draft" else ["Approved"]
        ):
            version = get(version_path)
            send(
                "POST",
                version_path + "/lifecycle",
                {
                    "status": next_status,
                    "reviewer": REVIEWER,
                    "expected_revision": version["content_revision"],
                },
            )

    approved = get(version_path)
    if approved.get("status") != "Approved":
        raise SetupError("Pinned Profile did not reach Approved")
    expected = {
        "issue32-synthetic-environment",
        "issue32-synthetic-scope",
        "issue32-synthetic-location",
        "issue32-synthetic-vendor",
        "issue32-synthetic-process",
    }
    actual = {item["client_key"] for item in approved.get("items", [])}
    if not expected <= actual:
        raise SetupError("Approved Profile is missing synthetic SRA inventory")


def ensure_scope() -> int:
    workspace = get(f"/api/projects/{PROJECT_ID}/sra")
    profile_id = workspace.get("profile_version_id")
    if profile_id != PROFILE_VERSION_ID:
        raise SetupError("SRA is not pinned to the approved Version 2 Profile")
    changed = 0
    for item in workspace.get("scope_items", []):
        # SQLite-backed responses serialize the boolean as integer 1.
        if item.get("included") == 1:
            continue
        send(
            "PUT",
            f"/api/projects/{PROJECT_ID}/sra/scope",
            {
                "profile_version_id": PROFILE_VERSION_ID,
                "scope_type": item["scope_type"],
                "target_key": item["target_key"],
                "included": True,
                "reviewed_by": REVIEWER,
            },
        )
        changed += 1
    if not workspace.get("scope_items"):
        raise SetupError("Approved Profile produced no SRA scope items")
    return changed


def ensure_risk() -> bool:
    risks = request_json("GET", f"/api/projects/{PROJECT_ID}/risks")
    if not isinstance(risks, list):
        raise SetupError("Risk endpoint did not return a list")
    matches = [risk for risk in risks if risk.get("title") == RISK_TITLE]
    if len(matches) > 1:
        raise SetupError("Duplicate deterministic synthetic risk exists")
    if matches:
        risk = matches[0]
        if (
            risk.get("profile_version_id") != PROFILE_VERSION_ID
            or risk.get("assessment_id") != ASSESSMENT_ID
        ):
            raise SetupError("Synthetic risk title exists with different ownership")
        return False

    stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    send(
        "POST",
        f"/api/projects/{PROJECT_ID}/risks",
        {
            "actor_id": "johnathan",
            "profile_version_id": PROFILE_VERSION_ID,
            "assessment_id": ASSESSMENT_ID,
            "title": RISK_TITLE,
            "threat": "Synthetic unauthorized access scenario for acceptance testing",
            "vulnerability": "Synthetic test gap in a hypothetical review cadence",
            "cia_impact": "Hypothetical confidentiality impact in synthetic data only",
            "safeguards": "Synthetic safeguards reviewed for this acceptance scenario",
            "corrective_action": "Document and review the synthetic access review cadence",
            "treatment": "corrective_action",
            "owner": REVIEWER,
            "status": "Open",
            "review_date": "2026-12-22",
            "inherent_likelihood": 1,
            "inherent_impact": 1,
            "residual_likelihood": 1,
            "residual_impact": 1,
            "reviewed_by": REVIEWER,
            "reviewed_at": stamp,
        },
    )
    return True


def ensure_determinations() -> tuple[int, int, dict]:
    index = get(f"/api/projects/{PROJECT_ID}/assessment")
    if index.get("id") != ASSESSMENT_ID:
        raise SetupError("Active assessment differs from the pinned assessment")
    records = [
        record
        for record in index.get("record_index", [])
        if record.get("carries_determination")
    ]
    if len(records) != 149:
        raise SetupError(f"Expected 149 determination records; got {len(records)}")

    updated = 0
    already = 0
    for record in records:
        record_id = record["record_id"]
        is_remediation = record_id == REMEDIATION_RECORD_ID
        expected_status = "Not Met" if is_remediation else "Met"
        observation = (
            NOT_MET_OBSERVATION
            if is_remediation
            else MET_OBSERVATION_PREFIX + record_id
        )
        path = (
            f"/api/projects/{PROJECT_ID}/assessments/{ASSESSMENT_ID}/records/"
            f"{quote(record_id, safe='')}"
        )
        detail = get(path)
        current = detail.get("determination", {})
        current_status = current.get("status", "")
        current_observation = current.get("interview_observation", "")
        if current_status == expected_status and current_observation == observation:
            already += 1
            continue
        if current_status:
            raise SetupError(
                f"Refusing to overwrite existing determination for {record_id}"
            )

        payload: dict[str, str] = {
            "status": expected_status,
            "interview_observation": observation,
        }
        if record.get("designation") == "addressable":
            payload["addressable_disposition"] = "standard_measure"
        send(
            "PUT",
            f"/api/assessments/{ASSESSMENT_ID}/determinations/{quote(record_id, safe='')}",
            payload,
        )
        updated += 1

    reconciliation_path = (
        f"/api/projects/{PROJECT_ID}/assessments/{ASSESSMENT_ID}/records/"
        f"{quote(REMEDIATION_RECORD_ID, safe='')}/reconciliation"
    )
    reconciliation = get(reconciliation_path)
    if not reconciliation.get("finding_id") or not reconciliation.get(
        "corrective_action_id"
    ):
        send(
            "PUT",
            reconciliation_path,
            {
                "outcome": "create",
                "title": FINDING_TITLE,
                "description": "Synthetic Issue 32 acceptance finding; no client facts.",
                "action_title": ACTION_TITLE,
                "action_description": (
                    "Synthetic acceptance action; document the hypothetical access review cadence."
                ),
            },
        )
    else:
        linked = reconciliation.get("links", [])
        titles = {item.get("title") for item in linked}
        if titles and not {FINDING_TITLE, ACTION_TITLE} <= titles:
            raise SetupError("Remediation record is linked to an unrelated finding or action")
    return updated, already, get(reconciliation_path)


def main() -> int:
    health = get("/api/health")
    if health.get("status") != "ok":
        raise SetupError("Packaged app health check did not return status=ok")

    overview = get(f"/api/projects/{PROJECT_ID}/profile")
    if overview.get("project_id") != PROJECT_ID:
        raise SetupError("Pinned project is not available on this app instance")
    version = get(f"/api/projects/{PROJECT_ID}/profile/versions/{PROFILE_VERSION_ID}")
    if version.get("project_id") != PROJECT_ID:
        raise SetupError("Pinned Version 2 draft does not belong to this project")
    assessment = get(f"/api/projects/{PROJECT_ID}/assessment")
    if assessment.get("id") != ASSESSMENT_ID:
        raise SetupError("Pinned assessment does not match the active project assessment")
    if assessment.get("project", {}).get("name") != PROJECT_NAME:
        raise SetupError("Project name guard failed; no writes were made")

    # Do not query or modify assessment prompt endpoints: the earlier saved
    # question answer remains untouched by this script.
    ensure_profile()
    scope_updates = ensure_scope()
    risk_created = ensure_risk()
    determinations_updated, determinations_reused, reconciliation = ensure_determinations()
    readiness = get(
        f"/api/projects/{PROJECT_ID}/assessments/{ASSESSMENT_ID}/close-readiness"
    )
    if readiness.get("ready") is not True or readiness.get("blockers"):
        codes = [blocker.get("code") for blocker in readiness.get("blockers", [])]
        raise SetupError(f"Fieldwork close readiness is not Ready; blockers={codes}")

    print(
        json.dumps(
            {
                "project_id": PROJECT_ID,
                "assessment_id": ASSESSMENT_ID,
                "profile_version_id": PROFILE_VERSION_ID,
                "profile_status": "Approved",
                "records_total": assessment["framework"]["record_count"],
                "determination_records": 149,
                "determinations_updated": determinations_updated,
                "determinations_reused": determinations_reused,
                "sra_scope_reviews_added": scope_updates,
                "risk_created": risk_created,
                "remediation_reconciled": bool(
                    reconciliation.get("finding_id")
                    and reconciliation.get("corrective_action_id")
                ),
                "close_readiness": readiness.get("status"),
                "blockers": len(readiness.get("blockers", [])),
                "prompt_answers_touched": 0,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SetupError as error:
        print(f"Synthetic fieldwork setup stopped safely: {error}", file=sys.stderr)
        raise SystemExit(1) from error
