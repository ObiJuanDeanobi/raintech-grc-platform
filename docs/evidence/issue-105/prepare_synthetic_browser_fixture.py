"""Create an isolated synthetic workspace for #105 CMMC scoring browser checks.

One CMMC project with every requirement Met except: AC.L2-3.1.1 (5 points,
Not Met, with a POA&M item), IA.L2-3.5.3 (partial credit recorded), and one
Pending objective on AC.L2-3.1.2. Synthetic data only.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_m3_active_assessment_backend import create_assessment

OBSERVED = "Synthetic: observed with the administrator."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    root = parser.parse_args().data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    app = create_app(database_path=root / "workspace.db", storage_path=root / "files")
    with TestClient(app) as client:
        client_id = client.post("/api/clients", json={"name": "Synthetic Contractor A"}).json()[
            "id"
        ]
        project = client.post(
            f"/api/clients/{client_id}/projects",
            json={"name": "CMMC L2 2026", "framework_version_id": CMMC_FRAMEWORK_ID},
        ).json()["id"]
        assessment = create_assessment(client, project)
        workspace = client.get(f"/api/projects/{project}/assessment").json()
        objectives: dict[str, list[str]] = {}
        for record in workspace["record_index"]:
            if record["parent_id"]:
                objectives.setdefault(record["parent_id"], []).append(record["record_id"])

        def put(record: str, status: str) -> None:
            body = {"status": status, "interview_observation": OBSERVED if status == "Met" else ""}
            response = client.put(
                f"/api/assessments/{assessment}/determinations/{record}", json=body
            )
            assert response.status_code == 200, response.text

        for requirement, ids in objectives.items():
            for index, record in enumerate(ids):
                status = "Met"
                if requirement in {"AC.L2-3.1.1", "IA.L2-3.5.3"} and index == 0:
                    status = "Not Met"
                if requirement == "AC.L2-3.1.2" and index == 0:
                    status = "Pending"
                put(record, status)
        client.put(
            f"/api/assessments/{assessment}/records/AC.L2-3.1.1a/note",
            json={"note": "Synthetic: the authorized user list is out of date."},
        )
        base = f"/api/projects/{project}/assessments/{assessment}/requirements"
        client.put(
            f"{base}/IA.L2-3.5.3/partial-implementation",
            json={
                "implementation": "partial",
                "rationale": "Synthetic: MFA for privileged users only.",
            },
        )
        client.post(
            f"{base}/AC.L2-3.1.1/poam",
            json={
                "title": "Rebuild and review the authorized user list",
                "description": "Synthetic.",
            },
        )
        score = client.get(f"/api/projects/{project}/assessments/{assessment}/cmmc-score").json()
    print(json.dumps({"project": project, "score": score["score"], "complete": score["complete"]}))


if __name__ == "__main__":
    main()
