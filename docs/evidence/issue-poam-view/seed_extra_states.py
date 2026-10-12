"""Extra synthetic POA&M states on top of seed_synthetic_projects.py (half or hipaa)."""

import json
import os
import sys
import urllib.request

BASE = os.environ["API_BASE"]
project, assessment, mode = sys.argv[1:4]


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


def move(action, state):
    call(
        "PUT",
        f"/api/projects/{project}/corrective-actions/{action}",
        {"actor_id": "johnathan", "state": state},
    )


if mode == "half":
    base = f"/api/projects/{project}/assessments/{assessment}/requirements"
    ids = {}
    for req, title in [
        ("AC.L2-3.1.3", "Document and enforce CUI flow rules"),
        ("AU.L2-3.3.2", "Turn on per-user audit logging"),
        ("AU.L2-3.3.5", "Correlate audit records across systems"),
    ]:
        ids[req] = call("POST", f"{base}/{req}/poam", {"title": title})["poam_items"][-1]["id"]
    move(ids["AC.L2-3.1.3"], "Ready for Validation")
    move(ids["AU.L2-3.3.5"], "Withdrawn")
    # AU.L2-3.3.2 is closed once the requirement is Met.
    detail = call("GET", f"/api/projects/{project}/assessments/{assessment}/records/AU.L2-3.3.2")
    for child in detail["children"]:
        call(
            "PUT",
            f"/api/assessments/{assessment}/determinations/{child['record_id']}",
            {"status": "Met", "interview_observation": "Synthetic: observed with the IT lead."},
        )
    call(
        "POST",
        f"{base}/AU.L2-3.3.2/poam/{ids['AU.L2-3.3.2']}/close",
        {"rationale": "Per-user audit logging confirmed on all servers; sample log reviewed."},
    )
else:
    idx = call("GET", f"/api/projects/{project}/assessment")["work_list"]
    states = call("GET", f"/api/projects/{project}/assessment")["record_states"]
    todo = [
        r
        for r in idx
        if r["editable_determination"] and states.get(r["record_id"], {}).get("status") == "Not Met"
    ]
    for n, rec in enumerate(todo[:6]):
        saved = call(
            "PUT",
            f"/api/projects/{project}/assessments/{assessment}/records/{rec['record_id']}/reconciliation",
            {
                "outcome": "create",
                "title": f"Gap: {rec['citation']}",
                "action_title": f"Remediate {rec['title']}",
            },
        )
        if n == 1:
            move(saved["corrective_action_id"], "In Progress")
        if n == 2:
            move(saved["corrective_action_id"], "Ready for Validation")
        if n == 3:
            move(saved["corrective_action_id"], "Waiting")
        if n == 4:
            move(saved["corrective_action_id"], "Withdrawn")
        if n == 5:
            # Marked Not needed afterwards: the action stays open work but is no longer linked.
            call(
                "PUT",
                f"/api/projects/{project}/assessments/{assessment}/records/{rec['record_id']}"
                "/reconciliation",
                {"outcome": "not_needed", "rationale": "Synthetic: out of scope for this client."},
            )
print("ok")
