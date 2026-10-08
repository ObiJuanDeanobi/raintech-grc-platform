"""Seed one synthetic CMMC project through the public API for the #140 screenshots.

No real client data. AC.L2-3.1.1 is fully Met (one objective with mapped
evidence), AC.L2-3.1.2[a] is Not Met with labelled examine/interview/test notes,
AC.L2-3.1.3[a] is Pending. The workspace should open on AC.L2-3.1.2.
"""

import json
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8000"
OBSERVED = "Synthetic: observed the account list with the administrator."


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def upload(project: str, name: str, content: bytes) -> str:
    boundary = "----synthetic140"
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
    {"name": "CMMC L2 2026 (synthetic)", "framework_version_id": "cmmc-l2-ag-v2.13"},
)["id"]
call(
    "POST",
    f"/api/projects/{project}/profile-readiness/transitions",
    {"next_state": "Intake complete", "decision_note": "Synthetic intake for #140 evidence."},
)
assessment = call("POST", f"/api/projects/{project}/assessments")["id"]
for letter in "abcdef":
    call(
        "PUT",
        f"/api/assessments/{assessment}/determinations/AC.L2-3.1.1{letter}",
        {"status": "Met", "interview_observation": OBSERVED},
    )
call("PUT", f"/api/assessments/{assessment}/determinations/AC.L2-3.1.2a", {"status": "Not Met"})
call("PUT", f"/api/assessments/{assessment}/determinations/AC.L2-3.1.3a", {"status": "Pending"})
artifact = upload(project, "synthetic-access-policy.txt", b"Synthetic access control policy.")
call(
    "POST",
    f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
    {
        "artifact_id": artifact,
        "record_id": "AC.L2-3.1.1a",
        "rationale": "Synthetic policy lists authorized users.",
    },
)
call(
    "PUT",
    f"/api/assessments/{assessment}/records/AC.L2-3.1.2a/note",
    {
        "note": "Examine: Synthetic role matrix v2.\nInterview: Synthetic IT lead.\n"
        "Test: Standard user could open the admin console."
    },
)
print(json.dumps({"project": project, "assessment": assessment}))
