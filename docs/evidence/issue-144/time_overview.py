"""Time the Overview endpoint on a synthetic project, before and after mapping evidence files.

The Overview calls the close check with the storage root, which re-hashes every
mapped evidence file. Synthetic bytes only. Set ``API_BASE`` to a served app that
was seeded with ``seed_synthetic_projects.py`` (MODE=half).
"""

import json
import os
import statistics
import time
import urllib.request
from typing import Any

BASE = os.environ.get("API_BASE", "http://127.0.0.1:18474")
FILES = int(os.environ.get("FILES", "20"))
SIZE_MB = int(os.environ.get("SIZE_MB", "2"))


def call(method: str, path: str, body: object | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"null")


def upload(project: str, name: str, content: bytes) -> str:
    boundary = "----synthetic144"
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


def timed(path: str, runs: int = 7) -> tuple[float, float]:
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        call("GET", path)
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples), max(samples)


client = call("GET", "/api/clients")[0]
project = client["projects"][0]["id"]
workspace = call("GET", f"/api/projects/{project}/assessment")
assessment = workspace["id"]
overview = f"/api/projects/{project}/assessments/{assessment}/overview"
close = f"/api/projects/{project}/assessments/{assessment}/close-readiness"

before = {"overview_ms": timed(overview), "close_readiness_ms": timed(close)}
objectives = [r["record_id"] for r in workspace["record_index"] if r["record_type"] == "objective"]
for number in range(FILES):
    artifact = upload(project, f"synthetic-{number}.bin", os.urandom(SIZE_MB * 1024 * 1024))
    call(
        "POST",
        f"/api/projects/{project}/assessments/{assessment}/evidence-mappings",
        {"artifact_id": artifact, "record_id": objectives[number], "rationale": "Synthetic."},
    )
after = {"overview_ms": timed(overview), "close_readiness_ms": timed(close)}
print(
    json.dumps(
        {
            "evidence_files": FILES,
            "size_mb_each": SIZE_MB,
            "records": len(workspace["record_index"]),
            "no_evidence_median_max_ms": before,
            "with_evidence_median_max_ms": after,
        },
        indent=2,
    )
)
