param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$legacyRoot = $PSScriptRoot
$workspaceRoot = (Resolve-Path (Join-Path $legacyRoot "..\..")).Path
$venvPath = Join-Path $workspaceRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    python -m venv $venvPath
}

& $pythonPath -m pip install -r (Join-Path $legacyRoot "requirements.txt")
$env:CMMC_TRACKER_DATA_DIR = Join-Path $workspaceRoot "data"

Push-Location $legacyRoot
try {
    & $pythonPath -m uvicorn cmmc_tracker.main:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
