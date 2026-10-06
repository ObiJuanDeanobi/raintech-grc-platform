"""Create an isolated synthetic workspace for #81 reopening browser checks.

Project A: reopened, revalidated, regenerated, and reissued (prior issue superseded).
Project B (second client): issued, ready to reopen.
Project C: reopened, revalidation still pending (close blocked).
Synthetic data only.
"""

import argparse
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_m3_presentation_correction import _issue, _sign
from api.tests.test_issue_m3_substantive_reopening import _issued_with_not_met, _reopen


def _records(db: Path, assessment: str) -> list[str]:
    with sqlite3.connect(db) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT record_id FROM determinations WHERE assessment_id=? "
                "AND status='Met' ORDER BY record_id LIMIT 2",
                (assessment,),
            )
        ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    root = parser.parse_args().data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    db, files = root / "workspace.db", root / "files"
    app = create_app(database_path=db, storage_path=files, backup_path=files / "backups")
    with TestClient(app) as client:
        a, a_assessment, a_package, _ = _issued_with_not_met(client, db, "reopen-a")
        reopened = _reopen(client, a, a_package, affected=_records(db, a_assessment)[:1]).json()
        successor = reopened["successor_assessment_id"]
        for item in reopened["revalidation_items"]:
            client.post(
                f"/api/projects/{a}/assessments/{successor}/records/{item['record_id']}/revalidate",
                json={"actor_id": "johnathan", "note": "Re-examined with current evidence."},
            )
        regenerated = client.post(f"/api/projects/{a}/assessments/{successor}/packages").json()
        _sign(client, a, regenerated["id"])
        assert _issue(client, a, regenerated["id"]).status_code == 201
        b, _, b_package, _ = _issued_with_not_met(client, db, "reopen-b")
        c, c_assessment, c_package, _ = _issued_with_not_met(client, db, "reopen-c")
        _reopen(client, c, c_package, affected=_records(db, c_assessment)[:2])
    print(
        json.dumps(
            {"project_a": a, "superseded": a_package, "current": regenerated["id"],
             "project_b": b, "project_b_package": b_package, "project_c": c},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
