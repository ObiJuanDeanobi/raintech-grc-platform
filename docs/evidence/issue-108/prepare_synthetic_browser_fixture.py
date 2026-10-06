"""Synthetic CMMC projects for close-gate and issuance browser checks (Issue #108).

Project A (blocked): one requirement Not Met with an open POA&M item, no SSP.
Project B (issued): remediated, POA&M closed, SSP approved, package issued.
Synthetic data only.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_issue_108_cmmc_close_issue import _issuable, _ready_project, _sign
from api.tests.test_issue_m3_presentation_correction import _issue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    root = parser.parse_args().data_dir.resolve()
    if root.exists():
        raise SystemExit(f"Choose a new fixture directory: {root}")
    root.mkdir(parents=True)
    files = root / "files"
    app = create_app(
        database_path=root / "workspace.db", storage_path=files, backup_path=files / "backups"
    )
    with TestClient(app) as client:
        blocked, _, _ = _ready_project(client, "a-blocked")
        issued, _, package = _issuable(client, "b-issued")
        _sign(client, issued, package["id"])
        assert _issue(client, issued, package["id"]).status_code == 201
    print(json.dumps({"blocked": blocked, "issued": issued, "package": package["id"]}))


if __name__ == "__main__":
    main()
