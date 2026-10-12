"""Seed one synthetic half-done CMMC project through the public API for the #146 evidence.

No real client data. Serve the API first (see capture_screenshots.mjs) and set
``API_BASE``. Run from the repository root with the repo on ``PYTHONPATH`` (it reuses
the test suite's synthetic Profile payload):

    API_BASE=http://127.0.0.1:18482 python docs/evidence/issue-146/seed_half_done.py

State: the Profile is approved (its unknown resolved), because the Profile stays a hard
gate. In the assessment, Access Control, Awareness and Audit objectives are decided:
most requirements Met by documented observation, five Not Met (one with a POA&M draft,
one with an open POA&M item, the rest with none), and two Met with nothing yet to verify
them (evidence pending). In MODE=half everything else is not yet assessed; in
MODE=decided every other objective is Met by documented observation.
"""

import json
import os
import urllib.request
from typing import Any

from api.tests.test_issue_62_versioned_profile import resolved_profile_payload

BASE = os.environ.get("API_BASE", "http://127.0.0.1:18482")
OBSERVED = "Synthetic: observed with the IT lead."
NOT_MET = ["AC.L2-3.1.3", "AC.L2-3.1.5", "AC.L2-3.1.7", "AU.L2-3.3.2", "AU.L2-3.3.5"]
EVIDENCE_PENDING = ["AT.L2-3.2.1", "AU.L2-3.3.1"]
# MODE=half leaves most families blank (finalize is blocked); MODE=decided decides every
# objective, with the same gaps, so a gap assessment can be finalized.
MODE = os.environ.get("MODE", "half")
DECIDED_FAMILIES = ("AC", "AU", "AT") if MODE == "half" else ("",)


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


client = call("POST", "/api/clients", {"name": "Synthetic Defense Co"})["id"]
project = call(
    "POST",
    f"/api/clients/{client}/projects",
    {"name": "CMMC L2 2026 (synthetic, half done)", "framework_version_id": "cmmc-l2-ag-v2.13"},
)["id"]
draft = call("GET", f"/api/projects/{project}/profile")["versions"][0]
call(
    "PUT",
    f"/api/projects/{project}/profile/versions/{draft['id']}",
    resolved_profile_payload(draft["content_revision"]),
)
fresh = call("GET", f"/api/projects/{project}/profile/versions/{draft['id']}")
call(
    "POST",
    f"/api/projects/{project}/profile/versions/{draft['id']}/lifecycle",
    {"status": "Approved", "reviewer": "Johnathan", "expected_revision": fresh["content_revision"]},
)
assessment = call("POST", f"/api/projects/{project}/assessments")["id"]
for record in call("GET", f"/api/projects/{project}/assessment")["record_index"]:
    if record["record_type"] != "objective":
        continue
    requirement = record["parent_id"]
    if not requirement.startswith(DECIDED_FAMILIES):
        continue
    if requirement in NOT_MET:
        body = {"status": "Not Met", "interview_observation": "Synthetic: not in place yet."}
    elif requirement in EVIDENCE_PENDING:
        body = {"status": "Met"}
    else:
        body = {"status": "Met", "interview_observation": OBSERVED}
    call("PUT", f"/api/assessments/{assessment}/determinations/{record['record_id']}", body)
base = f"/api/projects/{project}/assessments/{assessment}/requirements"
call("POST", f"{base}/AC.L2-3.1.5/poam", {"draft": True})
call("POST", f"{base}/AC.L2-3.1.7/poam", {"title": "Review session lock settings"})
print(json.dumps({"project": project, "assessment": assessment}))
