"""Seed two synthetic CMMC projects through the public API for the #141 screenshots.

No real client data. Serve the API first with
``python docs/evidence/issue-140/serve_synthetic_api.py <empty-dir>``.

Project "Fieldwork" (fails 32 CFR 170.21(a)(2)(ii)):
- every requirement verified Met by a documented observation, except
- AC.L2-3.1.1: all six objectives Met, [a] with mapped evidence, [b]-[f]
  evidence pending (5 points out of the verified score only);
- AC.L2-3.1.2[a] Not Met (5); AC.L2-3.1.3 Not Met (1);
- IA.L2-3.5.9 Met, evidence pending (1);
- SC.L2-3.13.11 Not Met, encryption employed but not FIPS-validated (3).
Verified 110 - 5 - 5 - 1 - 1 - 3 = 95; projected 110 - 5 - 1 - 3 = 101.

Project "Conditional" (passes every 170.21 check):
- every requirement verified Met, except AC.L2-3.1.3 Not Met (1),
  AU.L2-3.3.4 Met evidence pending (1), SC.L2-3.13.11 Not Met, partial (3).
Verified 105; projected 106.
"""

import json
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8000"
OBSERVED = "Synthetic: observed with the IT lead."


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def upload(project: str, name: str, content: bytes) -> str:
    boundary = "----synthetic141"
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


def seed(client_name: str, project_name: str, plan: dict[str, str]) -> dict[str, Any]:
    """``plan`` maps an objective or requirement ID to Met-pending / Not Met."""
    client = call("POST", "/api/clients", {"name": client_name})["id"]
    project = call(
        "POST",
        f"/api/clients/{client}/projects",
        {"name": project_name, "framework_version_id": "cmmc-l2-ag-v2.13"},
    )["id"]
    call(
        "POST",
        f"/api/projects/{project}/profile-readiness/transitions",
        {"next_state": "Intake complete", "decision_note": "Synthetic intake for #141."},
    )
    assessment = call("POST", f"/api/projects/{project}/assessments")["id"]
    index = call("GET", f"/api/projects/{project}/assessment")["record_index"]
    for record in index:
        if record["record_type"] != "objective":
            continue
        objective, requirement = record["record_id"], record["parent_id"]
        choice = plan.get(objective, plan.get(requirement, "verified"))
        body = (
            {"status": "Met", "interview_observation": OBSERVED}
            if choice == "verified"
            else {"status": "Met"}
            if choice == "pending"
            else {"status": "Not Met"}
        )
        call("PUT", f"/api/assessments/{assessment}/determinations/{objective}", body)
    return {"project": project, "assessment": assessment}


fieldwork = seed(
    "Synthetic Defense Co",
    "CMMC L2 2026 fieldwork (synthetic)",
    {
        "AC.L2-3.1.1": "pending",
        "AC.L2-3.1.2a": "not_met",
        "AC.L2-3.1.3": "not_met",
        "IA.L2-3.5.9": "pending",
        "SC.L2-3.13.11": "not_met",
    },
)
artifact = upload(fieldwork["project"], "synthetic-user-list.txt", b"Synthetic authorized users.")
call(
    "POST",
    f"/api/projects/{fieldwork['project']}/assessments/{fieldwork['assessment']}/evidence-mappings",
    {"artifact_id": artifact, "record_id": "AC.L2-3.1.1a", "rationale": "Synthetic user list."},
)
conditional = seed(
    "Synthetic Machining LLC",
    "CMMC L2 2026 conditional (synthetic)",
    {"AC.L2-3.1.3": "not_met", "AU.L2-3.3.4": "pending", "SC.L2-3.13.11": "not_met"},
)
for seeded in (fieldwork, conditional):
    call(
        "PUT",
        f"/api/projects/{seeded['project']}/assessments/{seeded['assessment']}"
        "/requirements/SC.L2-3.13.11/partial-implementation",
        {
            "implementation": "partial",
            "rationale": "Synthetic: TLS in use, module not FIPS-validated.",
        },
    )
scores = {
    name: call(
        "GET", f"/api/projects/{seeded['project']}/assessments/{seeded['assessment']}/cmmc-score"
    )
    for name, seeded in (("fieldwork", fieldwork), ("conditional", conditional))
}
print(
    json.dumps(
        {
            name: {
                "verified": score["verified"]["arithmetic"],
                "projected": score["projected"]["arithmetic"],
                "eligible": score["conditional"]["eligible"],
                "checks": {c["key"]: c["passed"] for c in score["conditional"]["checks"]},
            }
            for name, score in scores.items()
        },
        indent=2,
        ensure_ascii=False,
    )
)
