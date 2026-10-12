"""Display flags never enter the package source snapshot (ADR 0022).

A CMMC version finalized before the flow-alignment build stored a score without the new
display keys. A presentation-only correction compares the live source with the stored
one by content hash, so the display keys must stay outside the snapshotted score.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from api import cmmc
from api.tests.test_issue_108_cmmc_close_issue import _client, _issuable, _sign
from api.tests.test_issue_m3_presentation_correction import _correct, _issue

DISPLAY_KEYS = {"started", "all_decided", "check_flags", "hints"}


def test_correction_of_a_pre_change_cmmc_version_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = cmmc.score

    def old_shape(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result: dict[str, Any] = original(*args, **kwargs)
        return {key: value for key, value in result.items() if key not in DISPLAY_KEYS}

    with _client(tmp_path) as client:
        project, _assessment, package = _issuable(client, "old-shape")
        _sign(client, project, package["id"])
        # Finalize as the code did before this build: no display keys in the score.
        monkeypatch.setattr(cmmc, "score", old_shape)
        assert _issue(client, project, package["id"]).status_code == 201
        monkeypatch.setattr(cmmc, "score", original)
        corrected = _correct(client, project, package["id"], reason="Fix report title spacing.")
        assert corrected.status_code == 201, corrected.text


def test_new_snapshots_do_not_contain_display_keys(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        project, _assessment, package = _issuable(client, "new-shape")
        _sign(client, project, package["id"])
        assert _issue(client, project, package["id"]).status_code == 201
    with sqlite3.connect(tmp_path / "workspace.db") as connection:
        stored = [row[0] for row in connection.execute("SELECT source_json FROM source_snapshots")]
    assert stored
    for source_json in stored:
        score = json.loads(source_json)["cmmc"]["score"]
        assert not DISPLAY_KEYS & set(score)
