"""Focused tests for the production Windows launcher boundary."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import windows_launcher


def test_data_root_uses_override(monkeypatch: Any, tmp_path: Path) -> None:
    target = tmp_path / "isolated data"
    monkeypatch.setenv("RAINTECH_DATA_DIR", str(target))
    assert windows_launcher.data_root() == target.resolve()


def test_build_app_serves_ui_and_uses_isolated_data(monkeypatch: Any, tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    (resources / "dist").mkdir(parents=True)
    (resources / "dist" / "index.html").write_text("<h1>RainTech</h1>", encoding="utf-8")
    captured: dict[str, Any] = {}

    def fake_create_app(**kwargs: Any) -> FastAPI:
        captured.update(kwargs)
        return FastAPI()

    monkeypatch.setattr(windows_launcher, "resource_root", lambda: resources)
    monkeypatch.setattr(windows_launcher, "create_app", fake_create_app)
    monkeypatch.setenv("RAINTECH_DATA_DIR", str(tmp_path / "data"))
    holder: dict[str, Any] = {"server": type("Server", (), {"should_exit": False})()}
    with TestClient(windows_launcher.build_app(holder)) as client:
        assert client.get("/api/app/status").json()["product"] == windows_launcher.PRODUCT
        assert "RainTech" in client.get("/").text
        assert client.post("/api/app/shutdown").json() == {"stopping": True}
        assert holder["server"].should_exit
    assert captured["database_path"] == tmp_path / "data" / "workspace.db"
    assert captured["storage_path"] == tmp_path / "data" / "files"


def test_main_reopens_exact_existing_instance(monkeypatch: Any) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        windows_launcher, "instance_status", lambda _port: {"product": windows_launcher.PRODUCT}
    )
    monkeypatch.setattr(webbrowser, "open", opened.append)
    assert windows_launcher.main() == 0
    assert opened == [f"http://{windows_launcher.HOST}:{windows_launcher.DEFAULT_PORT}/"]


def test_main_rejects_unrelated_port_occupant(monkeypatch: Any) -> None:
    monkeypatch.setattr(windows_launcher, "instance_status", lambda _port: None)
    monkeypatch.setattr(windows_launcher, "port_is_available", lambda _port: False)
    try:
        windows_launcher.main()
    except RuntimeError as error:
        assert "another application" in str(error)
    else:
        raise AssertionError("Expected an occupied-port error")
