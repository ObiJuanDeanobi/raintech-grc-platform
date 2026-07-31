"""Throwaway Windows packaging entry point for GitHub Issue #32."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.main import create_app

HOST = "127.0.0.1"
PORT = 18432


def bundle_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[2]


def user_data_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is required for the Windows package")
    return Path(local_app_data) / "RainTech" / "GRC Platform Spike"


def port_is_available() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((HOST, PORT)) != 0


def build_app(server_holder: dict[str, uvicorn.Server]) -> FastAPI:
    resources = bundle_root()
    mutable = user_data_root()
    mutable.mkdir(parents=True, exist_ok=True)
    app = create_app(
        database_path=mutable / "workspace.db",
        storage_path=mutable / "files",
        repository_root=resources,
    )

    @app.post("/api/app/shutdown")
    def shut_down() -> dict[str, bool]:
        server_holder["server"].should_exit = True
        return {"stopping": True}

    app.mount("/", StaticFiles(directory=resources / "dist", html=True), name="ui")
    return app


def open_browser_when_ready() -> None:
    health_url = f"http://{HOST}:{PORT}/api/health"
    for _ in range(120):
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(f"http://{HOST}:{PORT}/")
                    return
        except OSError:
            time.sleep(0.1)


def main() -> int:
    if not port_is_available():
        webbrowser.open(f"http://{HOST}:{PORT}/")
        return 0

    server_holder: dict[str, uvicorn.Server] = {}
    app = build_app(server_holder)
    config = uvicorn.Config(
        app,
        host=HOST,
        port=PORT,
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    server_holder["server"] = server
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    server.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        error_log = user_data_root() / "launcher-error.log"
        error_log.parent.mkdir(parents=True, exist_ok=True)
        error_log.write_text(traceback.format_exc(), encoding="utf-8")
        raise SystemExit(1) from None
