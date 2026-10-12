"""Packages issued before #146 must still review, reissue and correct (ADR 0023)."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.close import fieldwork_ready as real
from api.tests.test_issue_146_gap_package import _complete, _issue, _lifecycles, _source
from api.tests.test_issue_m3_hipaa_generation import _ready
from api.tests.test_issue_m3_hipaa_issue_backup import _app

OLD_READINESS_KEYS = {
    "target",
    "status",
    "ready",
    "checks",
    "blockers",
    "groups",
    "links",
    "framework_version_id",
    "project_id",
    "assessment_id",
    "informational",
}


@pytest.fixture(autouse=True)
def _no_double_submit_window(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.issuance as issuance

    monkeypatch.setattr(issuance, "DOUBLE_SUBMIT_SECONDS", 0)


def _old_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make generation write the readiness exactly as it was before #146."""

    def old(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = real(*args, **kwargs)
        result.pop("package_type", None)
        result.pop("deferred", None)
        return result

    monkeypatch.setattr("api.generation.fieldwork_ready", old)


def _drift(client: TestClient, project: str, package: str) -> list[str]:
    review = client.get(f"/api/projects/{project}/packages/{package}/review")
    assert review.status_code == 200, review.text
    drift: list[str] = review.json()["drift"]
    return drift


def test_readiness_close_snapshot_has_the_pre_146_readiness_shape(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _complete(client, "compat-shape")
        issued = _issue(client, project, assessment, "readiness_close").json()
        readiness = _source(db, issued["package_id"])["readiness"]
        assert set(readiness) == OLD_READINESS_KEYS
        assert "package_type" not in _source(db, issued["package_id"])


def test_hipaa_snapshot_has_the_pre_146_readiness_shape(tmp_path: Path) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "compat-hipaa-shape")
        issued = _issue(client, project, assessment).json()
        assert set(_source(db, issued["package_id"])["readiness"]) == OLD_READINESS_KEYS


def test_a_pre_146_readiness_close_issue_has_no_drift_and_can_be_reissued(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _complete(client, "compat-cmmc")
        _old_shape(monkeypatch)
        first = _issue(client, project, assessment, "readiness_close").json()
        monkeypatch.undo()
        monkeypatch.setattr("api.issuance.DOUBLE_SUBMIT_SECONDS", 0)
        assert _drift(client, project, first["package_id"]) == []
        again = _issue(client, project, assessment, "readiness_close", "Reissued.")
        assert again.status_code == 201, again.text
        assert _lifecycles(client, project)[first["package_id"]] == "Superseded"


def test_a_pre_146_hipaa_issue_has_no_drift_and_can_be_reissued(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, db, _ = _app(tmp_path)
    with client:
        project, assessment = _ready(client, db, "compat-hipaa")
        _old_shape(monkeypatch)
        first = _issue(client, project, assessment).json()
        monkeypatch.undo()
        monkeypatch.setattr("api.issuance.DOUBLE_SUBMIT_SECONDS", 0)
        assert _drift(client, project, first["package_id"]) == []
        again = _issue(client, project, assessment, None, "Reissued.")
        assert again.status_code == 201, again.text
        corrected = client.post(
            f"/api/projects/{project}/packages/{again.json()['package_id']}/issue-now",
            json={"actor_id": "johnathan"},
        )
        assert corrected.status_code == 201, corrected.text
