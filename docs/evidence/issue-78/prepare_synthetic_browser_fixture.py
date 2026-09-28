"""Create an isolated three-project workspace for Issue #78 browser smoke checks."""

import argparse
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_workspace_api import create_workspace


def _assessment(client: TestClient, client_id: str, project_name: str) -> tuple[str, str]:
    project = client.post(
        f"/api/clients/{client_id}/projects", json={"name": project_name}
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    acknowledged = client.post(
        f"/api/projects/{project_id}/profile-readiness/acknowledgement"
    )
    assert acknowledged.status_code == 201, acknowledged.text
    transition = client.post(
        f"/api/projects/{project_id}/profile-readiness/transitions",
        json={"next_state": "Intake complete", "decision_note": "Synthetic fixture intake."},
    )
    assert transition.status_code == 201, transition.text
    assessment = client.post(f"/api/projects/{project_id}/assessments")
    assert assessment.status_code == 201, assessment.text
    return project_id, assessment.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    args = parser.parse_args()
    root = args.data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    db_path = root / "workspace.db"
    with TestClient(create_app(database_path=db_path, storage_path=root / "files")) as client:
        first_project, first_assessment = create_workspace(client)
        with sqlite3.connect(db_path) as connection:
            first_client = connection.execute(
                "SELECT client_id FROM projects WHERE id = ?", (first_project,)
            ).fetchone()[0]
        second_project, second_assessment = _assessment(
            client, first_client, "Synthetic Same-Client Project"
        )
        other_client = client.post("/api/clients", json={"name": "Synthetic Other Client"})
        assert other_client.status_code == 201, other_client.text
        third_project, third_assessment = _assessment(
            client, other_client.json()["id"], "Synthetic Cross-Client Project"
        )
    for label, project_id, assessment_id in (
        ("first", first_project, first_assessment),
        ("same-client", second_project, second_assessment),
        ("cross-client", third_project, third_assessment),
    ):
        print(f"{label}: project={project_id} active_assessment={assessment_id}")


if __name__ == "__main__":
    main()
