"""Create an isolated synthetic workspace for #80 correction browser checks.

Project A: first issue superseded by an issued presentation-only correction,
plus a stale correction whose reissue is blocked. Project B (another client):
one current issue and no corrections. Synthetic data only.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_m3_hipaa_issue_backup import _backup, _issued_candidate
from api.tests.test_issue_m3_presentation_correction import _correct, _issue, _sign


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    root = parser.parse_args().data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    db = root / "workspace.db"
    files = root / "files"
    app = create_app(database_path=db, storage_path=files, backup_path=files / "backups")
    with TestClient(app) as client:
        project, _, prior = _issued_candidate(client, db, "browser-a")
        assert _issue(client, project, prior["id"]).status_code == 201
        issued = _correct(client, project, prior["id"], reason="Correct cover date format.")
        stale = _correct(client, project, prior["id"], reason="Superseded draft correction.")
        issued_id, stale_id = issued.json()["package"]["id"], stale.json()["package"]["id"]
        _sign(client, project, issued_id)
        assert _issue(client, project, issued_id).status_code == 201
        _sign(client, project, stale_id)
        assert _backup(client, project, stale_id).status_code == 409
        other, _, other_package = _issued_candidate(client, db, "browser-b")
        assert _issue(client, other, other_package["id"]).status_code == 201
    print(
        json.dumps(
            {
                "project_a": project,
                "superseded": prior["id"],
                "current": issued_id,
                "stale": stale_id,
                "project_b": other,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
