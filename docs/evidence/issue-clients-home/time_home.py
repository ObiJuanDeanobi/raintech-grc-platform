"""Time GET /api/home. Run: PYTHONPATH=. python docs/evidence/issue-clients-home/time_home.py

Scenario A: 20 mixed projects (about two thirds CMMC, one third HIPAA, 60 determinations each).
Scenario B: 100 CMMC projects, every objective Pending except the last, which is Met (scoring
runs, and every requirement is Pending).
Scenario C: 100 CMMC projects, every objective Not Met except the last, which is Met.
Scenario D: 100 CMMC projects with nothing decided (no score is computed).
"""

import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app

CMMC = "cmmc-l2-ag-v2.13"
HIPAA = "hipaa-45cfr164-2026-07-01"


def app() -> tuple[TestClient, Path]:
    tmp = Path(tempfile.mkdtemp())
    return TestClient(create_app(database_path=tmp / "w.db", storage_path=tmp / "f")), tmp / "w.db"


def create(client: TestClient, number: int, framework: str) -> tuple[str, str]:
    client_id = client.post("/api/clients", json={"name": f"C{number}"}).json()["id"]
    project = client.post(
        f"/api/clients/{client_id}/projects",
        json={"name": f"P{number}", "framework_version_id": framework},
    ).json()["id"]
    started = client.post(f"/api/projects/{project}/start-assessment")
    assert started.status_code in (200, 201), started.text
    return project, client.get(f"/api/projects/{project}/assessment").json()["id"]


def measure(client: TestClient, label: str) -> None:
    times = []
    for _ in range(10):
        begin = time.perf_counter()
        home = client.get("/api/home").json()
        times.append((time.perf_counter() - begin) * 1000)
    print(
        f"{label}: {len(home['projects'])} projects; ms",
        [round(x) for x in times],
        "median",
        round(statistics.median(times)),
    )


def scenario_a() -> None:
    client, _ = app()
    with client:
        for n in range(20):
            framework = CMMC if n % 3 else HIPAA
            project, assessment = create(client, n, framework)
            body = (
                {"status": "Met", "interview_observation": "synthetic"}
                if framework == CMMC
                else {"status": "Not Met"}
            )
            records = client.get(f"/api/projects/{project}/assessment").json()["record_index"]
            decided = 0
            for record in records:
                if record.get("editable_determination") and decided < 60:
                    url = f"/api/assessments/{assessment}/determinations/{record['record_id']}"
                    client.put(url, json=body)
                    decided += 1
        measure(client, "A mixed")


def worst(label: str, fill: str | None) -> None:
    client, db = app()
    with client:
        made = [create(client, n, CMMC) for n in range(100)]
        with sqlite3.connect(db) as connection:
            objectives = [
                row[0]
                for row in connection.execute(
                    "SELECT record_id FROM framework_records WHERE framework_version_id = ?"
                    " AND carries_determination = 1",
                    (CMMC,),
                )
            ]
            if fill:
                for _, assessment in made:
                    connection.executemany(
                        "INSERT INTO determinations(assessment_id, record_id, status, updated_at)"
                        " VALUES (?, ?, ?, '2026-10-12T00:00:00+00:00')",
                        [(assessment, r, fill) for r in objectives[:-1]]
                        + [(assessment, objectives[-1], "Met")],
                    )
        measure(client, label)


scenario_a()
worst("B 100 CMMC, all Pending", "Pending")
worst("C 100 CMMC, all Not Met", "Not Met")
worst("D 100 CMMC, nothing decided", None)
