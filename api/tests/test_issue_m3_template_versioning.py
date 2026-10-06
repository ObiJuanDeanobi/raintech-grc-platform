"""Template versions are immutable once an issued package used them (Issue #100)."""

import shutil
import sqlite3
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

import api.generation as generation
from api.main import create_app
from api.tests.test_issue_m3_hipaa_issue_backup import _backup, _issued_candidate
from api.tests.test_issue_m3_presentation_correction import _correct, _issue, _sign


def _isolated(tmp_path: Path) -> tuple[TestClient, Path, Path, Path]:
    repository = Path(__file__).resolve().parents[2]
    isolated = tmp_path / "repository"
    for relative in (
        Path("catalog/versions/hipaa-45cfr164-2026-07-01.json"),
        Path("catalog/versions/hipaa-45cfr164-2026-07-01-prompts.json"),
        Path("catalog/versions/cmmc-l2-ag-v2.13.json"),
        Path("catalog/versions/cmmc-l2-ag-v2.13-guidance.json"),
        Path("docs/templates/hipaa/v2"),
    ):
        source, target = repository / relative, isolated / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    db, files = tmp_path / "db.sqlite", tmp_path / "files"
    app = create_app(
        database_path=db,
        storage_path=files,
        backup_path=files / "backups",
        repository_root=isolated,
    )
    return TestClient(app), db, files, isolated


def _issued(client: TestClient, db: Path, suffix: str) -> tuple[str, str, str]:
    project, assessment, package = _issued_candidate(client, db, suffix)
    assert _issue(client, project, package["id"]).status_code == 201
    return project, assessment, package["id"]


def test_issued_template_bytes_cannot_change_in_place(tmp_path: Path) -> None:
    client, db, _, repository = _isolated(tmp_path)
    with client:
        project, assessment, prior = _issued(client, db, "in-place")
        template = next((repository / "docs/templates/hipaa/v2").glob("*.docx"))
        template.write_bytes(template.read_bytes() + b"\nedited in place")
        generated = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert generated.status_code == 409
        assert "new template version" in generated.json()["detail"]
        corrected = _correct(client, project, prior)
        assert corrected.status_code == 409
        assert "new template version" in corrected.json()["detail"]
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM generated_packages").fetchone()[0] == 1


def test_unissued_template_version_can_still_change(tmp_path: Path) -> None:
    client, db, _, repository = _isolated(tmp_path)
    with client:
        project, assessment, _ = _issued_candidate(client, db, "draft-template")
        template = next((repository / "docs/templates/hipaa/v2").glob("*.docx"))
        template.write_bytes(template.read_bytes() + b"\ndraft change")
        generated = client.post(f"/api/projects/{project}/assessments/{assessment}/packages")
        assert generated.status_code == 201, generated.text


def test_new_version_corrects_prior_issue_and_both_stay_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, db, files, repository = _isolated(tmp_path)
    with client:
        project, _, prior = _issued(client, db, "new-version")
        v3 = repository / "docs/templates/hipaa/v3"
        v3.mkdir()
        names = []
        for kind, path in generation.template_files(repository, "hipaa-v2"):
            target = v3 / path.name.replace("_v2", "_v3")
            target.write_bytes(path.read_bytes())
            names.append((kind, target.name))
        monkeypatch.setitem(
            generation.TEMPLATE_VERSIONS, "hipaa-v3", ("docs/templates/hipaa/v3", tuple(names))
        )
        monkeypatch.setattr(generation, "CURRENT_TEMPLATE_VERSION", "hipaa-v3")

        corrected = _correct(client, project, prior)
        assert corrected.status_code == 201, corrected.text
        package = corrected.json()["package"]
        assert package["manifest"]["template_version"] == "hipaa-v3"
        prior_review = client.get(f"/api/projects/{project}/packages/{prior}/review").json()
        assert prior_review["drift"] == [] and prior_review["blockers"] == []
        _sign(client, project, package["id"])
        backup = _backup(client, project, package["id"])
        assert backup.status_code == 201, backup.text
        names_in_archive = ZipFile(files / "backups" / backup.json()["relative_path"]).namelist()
        assert any(name.startswith("template/v2/") for name in names_in_archive)
        assert any(name.startswith("template/v3/") for name in names_in_archive)
        issued = client.post(
            f"/api/projects/{project}/packages/{package['id']}/issue",
            json={"actor_id": "johnathan", "backup_id": backup.json()["id"]},
        )
        assert issued.status_code == 201, issued.text
    with sqlite3.connect(db) as connection:
        assert connection.execute(
            "SELECT template_version FROM generated_packages ORDER BY created_at"
        ).fetchall() == [("hipaa-v2",), ("hipaa-v3",)]
