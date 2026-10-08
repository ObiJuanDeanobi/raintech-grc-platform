"""Seed a synthetic CMMC project with an evidence library for the #142 screenshots.

No real client data. Serve the API first with
``python docs/evidence/issue-140/serve_synthetic_api.py <empty-dir>``.

Project "Evidence library (synthetic)":
- every requirement verified Met by a documented observation, except
- AC.L2-3.1.1: all six objectives Met with no observation; [a]-[c] linked to
  synthetic-access-control-policy.pdf in one bulk act, [d]-[f] to
  synthetic-network-diagram.png. The policy's review date is then moved into
  the past, so [a]-[c] return to evidence pending and the 5-point requirement
  leaves the verified score while the determinations stay Met.
- AC.L2-3.1.2[a]: Met, linked to synthetic-user-access-review.xlsx, review due
  in 12 days (inside the 30-day lead time): due soon, still verified.
- synthetic-incident-response-plan.docx: uploaded, not linked, no review date.
- synthetic-old-firewall-export.txt: in the recycle bin.
"""

import json
import urllib.request
from datetime import date, timedelta
from typing import Any

BASE = "http://127.0.0.1:8000"
OBSERVED = "Synthetic: observed with the IT lead."
TODAY = date.today()


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def upload(project: str, name: str, content: bytes) -> str:
    boundary = "----synthetic142"
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


def review(project: str, artifact: str, when: date | None) -> None:
    call(
        "PUT",
        f"/api/projects/{project}/evidence/{artifact}/review-date",
        {"review_date": when.isoformat() if when else None},
    )


def score(project: str, assessment: str) -> dict[str, Any]:
    result = call("GET", f"/api/projects/{project}/assessments/{assessment}/cmmc-score")
    return {
        "verified": result["verified"]["arithmetic"],
        "projected": result["projected"]["arithmetic"],
    }


client = call("POST", "/api/clients", {"name": "Synthetic Avionics Co"})["id"]
project = call(
    "POST",
    f"/api/clients/{client}/projects",
    {"name": "Evidence library (synthetic)", "framework_version_id": "cmmc-l2-ag-v2.13"},
)["id"]
call(
    "POST",
    f"/api/projects/{project}/profile-readiness/transitions",
    {"next_state": "Intake complete", "decision_note": "Synthetic intake for #142."},
)
assessment = call("POST", f"/api/projects/{project}/assessments")["id"]
index = call("GET", f"/api/projects/{project}/assessment")["record_index"]
for record in index:
    if record["record_type"] != "objective":
        continue
    unverified = record["parent_id"] == "AC.L2-3.1.1" or record["record_id"] == "AC.L2-3.1.2a"
    body = {"status": "Met"} if unverified else {"status": "Met", "interview_observation": OBSERVED}
    call("PUT", f"/api/assessments/{assessment}/determinations/{record['record_id']}", body)

policy = upload(
    project, "synthetic-access-control-policy.pdf", b"Synthetic access control policy v2025."
)
diagram = upload(project, "synthetic-network-diagram.png", b"Synthetic network diagram.")
access_review = upload(project, "synthetic-user-access-review.xlsx", b"Synthetic quarterly review.")
upload(project, "synthetic-incident-response-plan.docx", b"Synthetic IR plan.")
old = upload(project, "synthetic-old-firewall-export.txt", b"Synthetic old export.")
call("POST", f"/api/projects/{project}/evidence/{old}/recycle")

mappings = f"/api/projects/{project}/assessments/{assessment}/evidence-mappings/bulk"
call(
    "POST",
    mappings,
    {
        "artifact_id": policy,
        "record_ids": ["AC.L2-3.1.1a", "AC.L2-3.1.1b", "AC.L2-3.1.1c"],
        "rationale": "Synthetic: section 2 defines authorized users, processes and devices.",
    },
)
call(
    "POST",
    mappings,
    {
        "artifact_id": diagram,
        "record_ids": ["AC.L2-3.1.1d", "AC.L2-3.1.1e", "AC.L2-3.1.1f"],
        "rationale": "Synthetic: diagram shows enforced access paths.",
    },
)
call(
    "POST",
    mappings,
    {
        "artifact_id": access_review,
        "record_ids": ["AC.L2-3.1.2a"],
        "rationale": "Synthetic: quarterly access review lists permitted transactions.",
    },
)
review(project, policy, TODAY + timedelta(days=90))
review(project, diagram, TODAY + timedelta(days=200))
review(project, access_review, TODAY + timedelta(days=12))
before = score(project, assessment)
review(project, policy, TODAY - timedelta(days=8))  # the policy's review date passes
after = score(project, assessment)
states = call("GET", f"/api/projects/{project}/assessment")["record_states"]
print(
    json.dumps(
        {
            "project": project,
            "assessment": assessment,
            "policy_artifact": policy,
            "score_while_policy_current": before,
            "score_after_policy_stale": after,
            "AC.L2-3.1.1": states["AC.L2-3.1.1"],
            "AC.L2-3.1.1a": states["AC.L2-3.1.1a"],
            "AC.L2-3.1.2a": states["AC.L2-3.1.2a"],
        },
        indent=2,
        ensure_ascii=False,
    )
)
