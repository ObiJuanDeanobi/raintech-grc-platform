param(
    [ValidateSet("arm64", "x64")]
    [string]$Architecture = "x64"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SpikeRoot = $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ArmPython = "$env:LOCALAPPDATA\Programs\Python\Python312-arm64\python.exe"
$Pnpm = "C:\Users\johnathan\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd"
$NodeDirectory = "C:\Users\johnathan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"

if ($Architecture -eq "arm64") {
    if (-not (Test-Path -LiteralPath $ArmPython)) {
        throw "Install the official Python 3.12 ARM64 runtime first: $ArmPython"
    }
    # Keep the temporary toolchain path short because this checkout is already
    # deep enough to exceed Windows' legacy path limit during wheel extraction.
    $ArmEnvironment = Join-Path $env:LOCALAPPDATA "RainTech\PackageSpike\venv-arm64"
    if (-not (Test-Path -LiteralPath (Join-Path $ArmEnvironment "Scripts\python.exe"))) {
        & $ArmPython -m venv $ArmEnvironment
    }
    $Python = Join-Path $ArmEnvironment "Scripts\python.exe"
}
elseif (-not (Test-Path -LiteralPath $Python)) {
    throw "The repository x64 virtual environment is missing: $Python"
}
if (-not (Test-Path -LiteralPath $Pnpm)) {
    throw "The bundled pnpm runtime is missing: $Pnpm"
}
$env:Path = "$NodeDirectory;$env:Path"

Push-Location $RepoRoot
try {
    & $Pnpm build
    if ($LASTEXITCODE -ne 0) { throw "React production build failed" }

    & $Python -m pip install -e $RepoRoot
    if ($LASTEXITCODE -ne 0) { throw "Application dependency installation failed" }
    & $Python -m pip install "pyinstaller==6.21.0"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed" }

    $BuildRoot = Join-Path $env:LOCALAPPDATA "RainTech\PackageSpike"
    $Out = Join-Path $BuildRoot "out\$Architecture"
    $Work = Join-Path $BuildRoot "work\$Architecture"
    if (Test-Path -LiteralPath $Out) { Remove-Item -LiteralPath $Out -Recurse -Force }
    if (Test-Path -LiteralPath $Work) { Remove-Item -LiteralPath $Work -Recurse -Force }

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --windowed `
        --name "RainTechGRCSpike" `
        --distpath $Out `
        --workpath $Work `
        --specpath $Work `
        --add-data "$RepoRoot\dist;dist" `
        --add-data "$RepoRoot\catalog\versions;catalog\versions" `
        --add-data "$RepoRoot\migrations;migrations" `
        --add-data "$RepoRoot\alembic.ini;." `
        --collect-all "alembic" `
        "$SpikeRoot\launcher.py"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller packaging failed" }

    $Executable = Join-Path $Out "RainTechGRCSpike\RainTechGRCSpike.exe"
    Write-Host "Built: $Executable"
}
finally {
    Pop-Location
}
