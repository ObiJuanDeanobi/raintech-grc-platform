from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = Path(__file__).resolve().parent / "data" / "cmmc_l2_seed.json"


def data_dir() -> Path:
    return Path(os.environ.get("CMMC_TRACKER_DATA_DIR", PROJECT_ROOT / "data"))


def db_path() -> Path:
    return Path(os.environ.get("CMMC_TRACKER_DB", data_dir() / "tracker.db"))


def evidence_dir() -> Path:
    return data_dir() / "evidence"


def exports_dir() -> Path:
    return data_dir() / "exports"
