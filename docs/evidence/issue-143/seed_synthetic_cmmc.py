"""Seed a synthetic CMMC project through the public API for the #143 screenshots.

No real client data. Serve the API first, for example with
``python docs/evidence/issue-140/serve_synthetic_api.py <empty-dir>`` (port 8000),
or set ``API_BASE`` to another address.

The determinations follow the #141 "fieldwork" project
(``docs/evidence/issue-141/seed_synthetic_cmmc.py``): every requirement verified
Met by a documented observation, except

- AC.L2-3.1.2[a] Not Met (5 points; 32 CFR 170.21 never lets it stay on a POA&M),
  with examine and interview notes and one mapped evidence file;
- AC.L2-3.1.3 Not Met (1 point; POA&M-eligible);
- SC.L2-3.13.11 Not Met, encryption employed but not FIPS-validated (3 points;
  the named 170.21 exception, POA&M-eligible).

No POA&M item is created here: the screenshots show the one-click draft.
"""

import json
import os
import urllib.request
from typing import Any

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
OBSERVED = "Synthetic: observed with the IT lead."
NOT_MET = {"AC.L2-3.1.2a", "AC.L2-3.1.3"}


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def upload(project: str, name: str, content: bytes) -> str:
    boundary = "----synthetic143"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode()
    request = urllib.request.Request(
        f"{BASE}/api/projects/{project}/evidence",
        data=head + content + f"\r\n--{boundary}--\r\n".encode(),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request) as response:
        return str(json.loads(response.read())["id"])


client = call("POST", "/api/clients", {"name": "Synthetic Defense Co"})["id"]
project = call(
    "POST",
    f"/api/clients/{client}/projects",
    {"name": "CMMC L2 2026 POA&M (synthetic)", "framework_version_id": "cmmc-l2-ag-v2.13"},
)["id"]
call(
    "POST",
    f"/api/projects/{project}/profile-readiness/transitions",
    {"next_state": "Intake complete", "decision_note": "Synthetic intake for #143."},
)
assessment = call("POST", f"/api/projects/{project}/assessments")["id"]
index = call("GET", f"/api/projects/{project}/assessment")["record_index"]
for record in index:
    if record["record_type"] != "objective":
        continue
    objective, requirement = record["record_id"], record["parent_id"]
    failed = objective in NOT_MET or requirement in NOT_MET or requirement == "SC.L2-3.13.11"
    body = {"status": "Not Met"} if failed else {"status": "Met", "interview_observation": OBSERVED}
    call("PUT", f"/api/assessments/{assessment}/determinations/{objective}", body)

call(
    "PUT",
    f"/api/assessments/{assessment}/records/AC.L2-3.1.2a/note",
    {
        "note": "Examine: Synthetic: role matrix lists no transaction limits.\n"
        "Interview: Synthetic: IT lead confirms all users can approve payments."
    },
)
artifact = upload(project, "synthetic-role-matrix.txt", b"Synthetic role matrix.")
call(
    "POST",
    f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
    {"artifact_id": artifact, "record_id": "AC.L2-3.1.2a", "rationale": "Synthetic role matrix."},
)
call(
    "PUT",
    f"/api/projects/{project}/assessments/{assessment}/requirements/SC.L2-3.13.11"
    "/partial-implementation",
    {"implementation": "partial", "rationale": "Synthetic: TLS in use, module not FIPS-validated."},
)
workspace = call("GET", f"/api/projects/{project}/assessment")
score = call("GET", f"/api/projects/{project}/assessments/{assessment}/cmmc-score")
print(
    json.dumps(
        {
            "project": project,
            "assessment": assessment,
            "assessment_not_met_without_poam": workspace["not_met_without_poam"],
            "score_not_met_without_poam": score["not_met_without_poam"],
            "poam_eligibility": {
                line["record_id"]: [line["conditional_poam_allowed"], line["poam_reason"]]
                for line in score["deductions"]
            },
        },
        indent=2,
        ensure_ascii=False,
    )
)
