"""Synthetic CMMC project ready for SSP generation (Issue #107).

Approved Profile, every objective Met except AC.L2-3.1.1a (Not Met with a
POA&M item). Synthetic data only.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_107_cmmc_ssp import _assess_all, _project


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    root = parser.parse_args().data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    app = create_app(database_path=root / "workspace.db", storage_path=root / "files")
    with TestClient(app) as client:
        project, assessment = _project(client, "ssp-browser")
        _assess_all(client, project, assessment, failing="AC.L2-3.1.1a")
        client.post(
            f"/api/projects/{project}/assessments/{assessment}/requirements/AC.L2-3.1.1/poam",
            json={"title": "Rebuild the authorized user list"},
        )
    print(json.dumps({"project": project, "assessment": assessment}))


if __name__ == "__main__":
    main()
