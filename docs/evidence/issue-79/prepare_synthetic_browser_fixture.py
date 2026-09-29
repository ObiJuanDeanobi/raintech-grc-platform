"""Create isolated synthetic revisions and project identities for #79 Edge checks."""

import argparse
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app


def create_project(client: TestClient, client_id: str, name: str) -> tuple[str, str]:
    project = client.post(f"/api/clients/{client_id}/projects", json={"name": name})
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    acknowledged = client.post(
        f"/api/projects/{project_id}/profile-readiness/acknowledgement"
    )
    assert acknowledged.status_code == 201, acknowledged.text
    intake = client.post(
        f"/api/projects/{project_id}/profile-readiness/transitions",
        json={"next_state": "Intake complete", "decision_note": "Synthetic intake."},
    )
    assert intake.status_code == 201, intake.text
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
        first_client = client.post("/api/clients", json={"name": "Synthetic Client A"})
        assert first_client.status_code == 201, first_client.text
        second_client = client.post("/api/clients", json={"name": "Synthetic Client B"})
        assert second_client.status_code == 201, second_client.text
        first_project, first_revision = create_project(
            client, first_client.json()["id"], "Synthetic HIPAA Revision Project"
        )
        same_project, same_revision = create_project(
            client, first_client.json()["id"], "Synthetic Same Client Project"
        )
        cross_project, cross_revision = create_project(
            client, second_client.json()["id"], "Synthetic Cross Client Project"
        )
        successor = client.post(
            f"/api/projects/{first_project}/assessments/{first_revision}/successor",
            json={"actor_id": "johnathan", "reason": "Synthetic browser revision check."},
        )
        assert successor.status_code == 201, successor.text
        first_successor = successor.json()["id"]
        active = client.get(f"/api/projects/{first_project}/assessment")
        assert active.status_code == 200 and active.json()["id"] == first_successor
        for guessed in (same_revision, cross_revision):
            rejected = client.post(
                f"/api/projects/{first_project}/assessments/{guessed}/successor",
                json={"actor_id": "johnathan", "reason": "Synthetic guessed ID check."},
            )
            assert rejected.status_code == 404, rejected.text
        stale = client.post(
            f"/api/projects/{first_project}/assessments/{first_revision}/successor",
            json={"actor_id": "johnathan", "reason": "Synthetic stale ID check."},
        )
        assert stale.status_code == 409, stale.text
    with sqlite3.connect(db_path) as db:
        assert db.execute(
            "SELECT assessment_id FROM project_active_assessments WHERE project_id = ?",
            (first_project,),
        ).fetchone() == (first_successor,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    for label, project_id, assessment_id in (
        ("revision-project", first_project, first_successor),
        ("same-client", same_project, same_revision),
        ("cross-client", cross_project, cross_revision),
    ):
        print(f"{label}: project={project_id} active_assessment={assessment_id}")
    print(f"predecessor={first_revision}; guessed IDs rejected; stale ID rejected")


if __name__ == "__main__":
    main()
