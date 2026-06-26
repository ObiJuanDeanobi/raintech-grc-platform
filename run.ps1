param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn cmmc_tracker.main:app --host 127.0.0.1 --port $Port
