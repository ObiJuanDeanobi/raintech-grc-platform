"""Seed synthetic projects through the public API for the #145 screenshots.

No real client data. Serve the API first (see capture_screenshots.mjs) and set
``API_BASE``. Run from the repository root so the test helpers import.

Creates, in one workspace:

- ``HIPAA 2026 (ready to issue)``: Profile approved once, every determination decided,
  Security Risk Analysis complete. It also carries one Not Met with an open corrective
  action and one evidence file due for review in five days, so the Review and issue
  dialog shows two warnings and no hard gate. Its Profile has no unknown left.
- ``HIPAA 2026 (unknowns)``: Profile approved while it still records an unknown, so
  Profile complete is not recorded and the dialog lists it under "Must be fixed".
- ``HIPAA 2026 (draft only)``: started, Profile never approved, a few items decided.
- ``CMMC L2 2026 (draft only)``: started, Profile never approved, a few objectives decided.
"""

import json
import os
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

from api.tests.test_issue_62_versioned_profile import profile_payload, resolved_profile_payload
from api.tests.test_issue_m3_hipaa_sra import _risk

BASE = os.environ.get("API_BASE", "http://127.0.0.1:18460")
OBSERVED = "Synthetic: observed with the security officer."


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def upload(project: str, name: str, content: bytes) -> str:
    boundary = "----synthetic145"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    request = urllib.request.Request(
        f"{BASE}/api/projects/{project}/evidence",
        data=head + content + f"\r\n--{boundary}--\r\n".encode(),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request) as response:
        return str(json.loads(response.read())["id"])


def new_project(client_name: str, project_name: str, framework: str | None) -> str:
    client = call("POST", "/api/clients", {"name": client_name})["id"]
    body: dict[str, str] = {"name": project_name}
    if framework:
        body["framework_version_id"] = framework
    return str(call("POST", f"/api/clients/{client}/projects", body)["id"])


def decide(project: str, assessment: str, count: int, objective_only: bool) -> list[str]:
    work = call("GET", f"/api/projects/{project}/assessment")["work_list"]
    rows = [
        r
        for r in work
        if r["editable_determination"]
        and (not objective_only or r["record_type"] == "objective")
        and r["designation"] != "addressable"
    ]
    done = []
    for record in rows[:count]:
        call(
            "PUT",
            f"/api/assessments/{assessment}/determinations/{record['record_id']}",
            {"status": "Met", "interview_observation": OBSERVED},
        )
        done.append(record["record_id"])
    return done


# --- HIPAA, ready to issue (with warnings) ---------------------------------------------------
ready = new_project("Synthetic Health Clinic", "HIPAA 2026 (ready to issue)", None)
draft = call("GET", f"/api/projects/{ready}/profile")["versions"][0]
saved = call(
    "PUT",
    f"/api/projects/{ready}/profile/versions/{draft['id']}",
    resolved_profile_payload(draft["content_revision"]),
)
# One act: no review step, no reviewer typed. The account is the reviewer.
call(
    "POST",
    f"/api/projects/{ready}/profile/versions/{draft['id']}/lifecycle",
    {"status": "Approved", "expected_revision": saved["content_revision"]},
)
assessment = call("POST", f"/api/projects/{ready}/start-assessment")["assessment"]["id"]
for item in call("GET", f"/api/projects/{ready}/sra")["scope_items"]:
    call(
        "PUT",
        f"/api/projects/{ready}/sra/scope",
        {
            "profile_version_id": saved["id"],
            "scope_type": item["scope_type"],
            "target_key": item["target_key"],
            "included": True,
        },
    )
call("POST", f"/api/projects/{ready}/risks", _risk(saved["id"], assessment))
work = call("GET", f"/api/projects/{ready}/assessment")["work_list"]
first_required = None
for record in work:
    if not record["editable_determination"]:
        continue
    body: dict[str, Any] = {"status": "Met", "interview_observation": OBSERVED}
    if record["designation"] == "addressable":
        body["addressable_disposition"] = "standard_measure"
    call("PUT", f"/api/assessments/{assessment}/determinations/{record['record_id']}", body)
    if first_required is None and record["designation"] != "addressable":
        first_required = record["record_id"]
# Warnings: one Not Met with an open corrective action, and evidence due for review soon.
assert first_required is not None
call(
    "PUT",
    f"/api/assessments/{assessment}/determinations/{first_required}",
    {"status": "Not Met", "interview_observation": "Synthetic gap found during the walk-through."},
)
call(
    "PUT",
    f"/api/projects/{ready}/assessments/{assessment}/records/{first_required}/reconciliation",
    {
        "outcome": "create",
        "title": "Risk analysis is not current",
        "action_title": "Complete and document an enterprise-wide risk analysis",
        "rationale": "Synthetic gap needs remediation.",
    },
)
artifact = upload(ready, "security-policy.txt", b"synthetic policy text")
call(
    "POST",
    f"/api/projects/{ready}/assessments/{assessment}/evidence-mappings",
    {
        "artifact_id": artifact,
        "record_id": "164.308(a)(1)(ii)(A)",
        "rationale": "Synthetic policy supports the risk analysis.",
    },
)
call(
    "PUT",
    f"/api/projects/{ready}/evidence/{artifact}/review-date",
    {"review_date": (datetime.now(UTC) + timedelta(days=5)).date().isoformat()},
)

# --- HIPAA, Profile approved with an unknown still recorded -------------------------------------
unknown = new_project("Synthetic Health Clinic", "HIPAA 2026 (unknowns)", None)
unknown_draft = call("GET", f"/api/projects/{unknown}/profile")["versions"][0]
unknown_saved = call(
    "PUT",
    f"/api/projects/{unknown}/profile/versions/{unknown_draft['id']}",
    profile_payload(unknown_draft["content_revision"]),
)
approval = call(
    "POST",
    f"/api/projects/{unknown}/profile/versions/{unknown_draft['id']}/lifecycle",
    {"status": "Approved", "expected_revision": unknown_saved["content_revision"]},
)
print(json.dumps({"approval_message": approval["message"]}))
call("POST", f"/api/projects/{unknown}/start-assessment")

# --- HIPAA, draft only ------------------------------------------------------------------------
hipaa_draft = new_project("Synthetic Health Clinic", "HIPAA 2026 (draft only)", None)
hipaa_draft_assessment = call("POST", f"/api/projects/{hipaa_draft}/start-assessment")[
    "assessment"
]["id"]
decide(hipaa_draft, hipaa_draft_assessment, 6, objective_only=False)

# --- CMMC, draft only -------------------------------------------------------------------------
cmmc = new_project("Synthetic Defense Co", "CMMC L2 2026 (draft only)", "cmmc-l2-ag-v2.13")
cmmc_assessment = call("POST", f"/api/projects/{cmmc}/start-assessment")["assessment"]["id"]
decide(cmmc, cmmc_assessment, 14, objective_only=True)

print(
    json.dumps(
        {
            "ready": {"project": ready, "assessment": assessment},
            "hipaa_draft": {"project": hipaa_draft, "assessment": hipaa_draft_assessment},
            "cmmc_draft": {"project": cmmc, "assessment": cmmc_assessment},
        }
    )
)
