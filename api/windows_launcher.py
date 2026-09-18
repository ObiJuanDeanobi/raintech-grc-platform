"""Windows desktop entry point for the local RainTech GRC workspace."""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.main import create_app

HOST = "127.0.0.1"
DEFAULT_PORT = 18432
PRODUCT = "raintech-grc-platform"


def resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).resolve().parents[1]


def data_root() -> Path:
    override = os.environ.get("RAINTECH_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is required unless RAINTECH_DATA_DIR is set")
    return Path(local_app_data) / "RainTech" / "GRC Platform"


def configured_port() -> int:
    port = int(os.environ.get("RAINTECH_PORT", str(DEFAULT_PORT)))
    if not 1 <= port <= 65535:
        raise RuntimeError("RAINTECH_PORT must be between 1 and 65535")
    return port


def instance_status(port: int) -> dict[str, Any] | None:
    try:
        url = f"http://{HOST}:{port}/api/app/status"
        with urllib.request.urlopen(url, timeout=0.5) as response:
            if response.status == 200:
                value = json.loads(response.read())
                return value if isinstance(value, dict) else None
    except (OSError, ValueError, urllib.error.URLError):
        return None
    return None


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
    return True


def build_app(server_holder: dict[str, uvicorn.Server]) -> FastAPI:
    resources = resource_root()
    mutable = data_root()
    mutable.mkdir(parents=True, exist_ok=True)
    app = create_app(
        database_path=mutable / "workspace.db",
        storage_path=mutable / "files",
        repository_root=resources,
        backup_path=mutable / "files" / "backups",
    )

    @app.get("/api/app/status")
    def app_status() -> dict[str, str]:
        return {"product": PRODUCT, "status": "ready"}

    @app.post("/api/app/shutdown")
    def shutdown() -> dict[str, bool]:
        server_holder["server"].should_exit = True
        return {"stopping": True}

    ui = resources / "dist"
    if not (ui / "index.html").is_file():
        raise RuntimeError(f"Compiled UI is missing from {ui}")
    app.mount("/", StaticFiles(directory=ui, html=True), name="ui")
    return app


def open_browser_when_ready(port: int) -> None:
    if os.environ.get("RAINTECH_NO_BROWSER") == "1":
        return
    for _ in range(120):
        status = instance_status(port)
        if status and status.get("product") == PRODUCT:
            webbrowser.open(f"http://{HOST}:{port}/")
            return
        time.sleep(0.1)


def main() -> int:
    port = configured_port()
    status = instance_status(port)
    if status and status.get("product") == PRODUCT:
        if os.environ.get("RAINTECH_NO_BROWSER") != "1":
            webbrowser.open(f"http://{HOST}:{port}/")
        return 0
    if not port_is_available(port):
        raise RuntimeError(f"Port {port} is already occupied by another application")

    server_holder: dict[str, uvicorn.Server] = {}
    app = build_app(server_holder)
    server = uvicorn.Server(
        uvicorn.Config(app, host=HOST, port=port, log_config=None, access_log=False)
    )
    server_holder["server"] = server
    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    server.run()
    return 0


def run() -> int:
    try:
        return main()
    except Exception:
        log = data_root() / "logs" / "launcher-error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
