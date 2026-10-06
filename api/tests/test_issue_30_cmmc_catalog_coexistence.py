"""The CMMC catalog loads beside HIPAA without changing it (Issue #30)."""

import sqlite3
from pathlib import Path

from api.database import Database
from api.framework import CMMC_FRAMEWORK_ID, FRAMEWORK_ID, seed_cmmc_catalog, seed_framework

REPO_ROOT = Path(__file__).resolve().parents[2]


def _hipaa(database: Database) -> list[tuple[object, ...]]:
    with sqlite3.connect(database.path) as connection:
        return connection.execute(
            "SELECT * FROM framework_records WHERE framework_version_id=? ORDER BY record_id",
            (FRAMEWORK_ID,),
        ).fetchall()


def test_cmmc_catalog_coexists_with_hipaa_and_reseeds_idempotently(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db", tmp_path / "files")
    database.migrate()
    seed_framework(database, REPO_ROOT)
    before = _hipaa(database)
    seed_cmmc_catalog(database, REPO_ROOT)
    seed_cmmc_catalog(database, REPO_ROOT)
    assert _hipaa(database) == before
    with sqlite3.connect(database.path) as connection:
        counts = connection.execute(
            """SELECT record_type, COUNT(*), SUM(carries_determination)
               FROM framework_records WHERE framework_version_id=?
               GROUP BY record_type ORDER BY record_type""",
            (CMMC_FRAMEWORK_ID,),
        ).fetchall()
        orphans = connection.execute(
            """SELECT COUNT(*) FROM framework_records o
               WHERE o.framework_version_id=? AND o.record_type='objective'
                 AND NOT EXISTS (SELECT 1 FROM framework_records r
                                 WHERE r.framework_version_id=o.framework_version_id
                                   AND r.record_id=o.parent_id)""",
            (CMMC_FRAMEWORK_ID,),
        ).fetchone()[0]
    assert counts == [("objective", 320, 320), ("requirement", 110, 0)]
    assert orphans == 0
