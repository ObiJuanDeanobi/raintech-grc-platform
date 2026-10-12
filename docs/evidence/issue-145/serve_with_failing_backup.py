"""Serve the app with the pre-issuance backup made to fail, for the backup-failure screenshot.

Evidence only, never part of the product. The failure is injected the same way the
test suite does it (the archive validation raises), so the real failure path runs:
the failed backup is recorded, nothing is issued, and the API returns the 409 the
dialog shows. Usage, from the repository root:

    RAINTECH_DATA_DIR=<empty dir> RAINTECH_NO_BROWSER=1 RAINTECH_PORT=18461 \
        python docs/evidence/issue-145/serve_with_failing_backup.py
"""

import sys

import api.issuance as issuance
from api.windows_launcher import run


def _fail(*_args: object, **_kwargs: object) -> None:
    raise OSError("There is not enough free space on the backup drive.")


issuance._validate_archive = _fail  # type: ignore[assignment]
sys.exit(run())
