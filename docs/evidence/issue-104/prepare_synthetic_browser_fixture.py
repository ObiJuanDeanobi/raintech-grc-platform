"""Create an isolated synthetic workspace for #104 CMMC browser checks.

Client A: a CMMC project with AC.L2-3.1.1 objectives in mixed states, and a
HIPAA project. Client B: an untouched CMMC project. Synthetic data only.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID
from api.main import create_app
from api.tests.test_issue_m3_active_assessment_backend import create_assessment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    root = parser.parse_args().data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    app = create_app(database_path=root / "workspace.db", storage_path=root / "files")
    with TestClient(app) as client:

        def project(client_id: str, name: str, framework: str) -> str:
            response = client.post(
                f"/api/clients/{client_id}/projects",
                json={"name": name, "framework_version_id": framework},
            )
            return str(response.json()["id"])

        client_a = client.post("/api/clients", json={"name": "Synthetic Contractor A"}).json()["id"]
        client_b = client.post("/api/clients", json={"name": "Synthetic Contractor B"}).json()["id"]
        cmmc = project(client_a, "CMMC L2 2026", CMMC_FRAMEWORK_ID)
        hipaa = project(client_a, "HIPAA 2026", FRAMEWORK_ID)
        other = project(client_b, "CMMC L2 2026", CMMC_FRAMEWORK_ID)
        assessment = create_assessment(client, cmmc)
        for item in (hipaa, other):
            create_assessment(client, item)
        observed = "Synthetic: reviewed the account list with the administrator."
        for record, status in (
            ("AC.L2-3.1.1a", "Met"),
            ("AC.L2-3.1.1b", "Met"),
            ("AC.L2-3.1.1c", "Pending"),
            ("AC.L2-3.1.1d", "Not Met"),
        ):
            body = {"status": status, "interview_observation": observed if status == "Met" else ""}
            saved = client.put(f"/api/assessments/{assessment}/determinations/{record}", json=body)
            assert saved.status_code == 200, saved.text
    print(json.dumps({"cmmc": cmmc, "hipaa": hipaa, "other_client_cmmc": other}, indent=2))


if __name__ == "__main__":
    main()
