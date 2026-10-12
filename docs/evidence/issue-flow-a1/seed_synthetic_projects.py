"""Seed synthetic projects through the public API for the ADR 0022 Overview screenshots.

No real client data. Serve the API first (see capture_screenshots.mjs) and set
``API_BASE``. ``MODE`` is one of:

- ``new``: a CMMC project with intake complete and an assessment, nothing decided;
- ``half``: a CMMC project part way through: Access Control and Audit objectives
  decided (most Met by documented observation), five requirements Not Met, one
  of them with a POA&M draft and one with an Open item, everything else untouched;
- ``hipaa``: a HIPAA project with 30 records Not Met or Pending (Met needs evidence).
"""

import json
import os
import urllib.request
from typing import Any

BASE = os.environ.get("API_BASE", "http://127.0.0.1:18433")
MODE = os.environ.get("MODE", "new")
OBSERVED = "Synthetic: observed with the IT lead."
NOT_MET_REQUIREMENTS = ["AC.L2-3.1.3", "AC.L2-3.1.5", "AC.L2-3.1.7", "AU.L2-3.3.2", "AU.L2-3.3.5"]
DECIDED_FAMILIES = ("AC", "AU", "AT")


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def start(name: str, framework: str | None) -> tuple[str, str]:
    client = call("POST", "/api/clients", {"name": "Synthetic Defense Co"})["id"]
    body: dict[str, str] = {"name": name}
    if framework:
        body["framework_version_id"] = framework
    project = call("POST", f"/api/clients/{client}/projects", body)["id"]
    call(
        "POST",
        f"/api/projects/{project}/profile-readiness/transitions",
        {"next_state": "Intake complete", "decision_note": "Synthetic intake (ADR 0022)."},
    )
    assessment = call("POST", f"/api/projects/{project}/assessments")["id"]
    return project, assessment


if MODE == "new":
    project, assessment = start("CMMC L2 2026 (synthetic, new)", "cmmc-l2-ag-v2.13")
elif MODE == "half":
    project, assessment = start("CMMC L2 2026 (synthetic, half done)", "cmmc-l2-ag-v2.13")
    index = call("GET", f"/api/projects/{project}/assessment")["record_index"]
    for record in index:
        if record["record_type"] != "objective":
            continue
        requirement = record["parent_id"]
        if not requirement.startswith(DECIDED_FAMILIES):
            continue
        failed = requirement in NOT_MET_REQUIREMENTS
        body = (
            {"status": "Not Met"}
            if failed
            else {"status": "Met", "interview_observation": OBSERVED}
        )
        call(
            "PUT",
            f"/api/assessments/{assessment}/determinations/{record['record_id']}",
            body,
        )
    base = f"/api/projects/{project}/assessments/{assessment}/requirements"
    draft = call("POST", f"{base}/AC.L2-3.1.5/poam", {"draft": True})
    opened = call("POST", f"{base}/AC.L2-3.1.7/poam", {"title": "Review session lock settings"})
    print(
        json.dumps(
            {"draft": draft["poam_items"][0]["status"], "open": opened["poam_items"][0]["status"]}
        )
    )
    # Two more client projects, so the Overview's "Other client projects" list shows.
    other = call("POST", "/api/clients", {"name": "Tandem Clinic LLC"})["id"]
    call("POST", f"/api/clients/{other}/projects", {"name": "HIPAA 2026 (synthetic)"})
    call(
        "POST",
        f"/api/clients/{other}/projects",
        {"name": "CMMC L2 2026 (synthetic)", "framework_version_id": "cmmc-l2-ag-v2.13"},
    )
elif MODE == "hipaa":
    project, assessment = start("HIPAA 2026 (synthetic)", None)
    index = call("GET", f"/api/projects/{project}/assessment")["work_list"]
    deciding = [
        record
        for record in index
        if record["editable_determination"] and record["designation"] != "addressable"
    ]
    for number, record in enumerate(deciding[:30]):
        status = ["Not Met", "Pending", "Pending"][number % 3]
        call(
            "PUT",
            f"/api/assessments/{assessment}/determinations/{record['record_id']}",
            {"status": status},
        )
else:
    raise SystemExit(f"Unknown MODE {MODE}")

print(json.dumps({"project": project, "assessment": assessment}))
