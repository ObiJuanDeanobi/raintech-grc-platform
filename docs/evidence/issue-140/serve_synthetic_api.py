"""Run the API against a throwaway synthetic workspace for the #140 screenshots.

Usage (from the repository root, with the dev install active):
    python docs/evidence/issue-140/serve_synthetic_api.py <empty-data-dir>
then `pnpm run dev` and `python docs/evidence/issue-140/seed_synthetic_cmmc.py`.
"""

import sys
from pathlib import Path

import uvicorn

from api.main import create_app

data = Path(sys.argv[1]).resolve()
app = create_app(
    database_path=data / "workspace.db",
    storage_path=data / "files",
    repository_root=Path.cwd(),
)
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
