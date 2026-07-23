$ErrorActionPreference = "Stop"
$prototypeRoot = $PSScriptRoot
$bundledRuntimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
$bundledNodePath = Join-Path $bundledRuntimeRoot "node\bin"
$bundledToolsPath = Join-Path $bundledRuntimeRoot "bin"

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    $bundledPnpm = Join-Path $bundledToolsPath "pnpm.cmd"
    if (-not (Test-Path -LiteralPath $bundledPnpm)) {
        throw "pnpm was not found. Install Node.js with pnpm, then run this command again."
    }
    $env:PATH = "$bundledNodePath;$bundledToolsPath;$env:PATH"
}

Set-Location -LiteralPath $prototypeRoot
if (-not (Test-Path -LiteralPath (Join-Path $prototypeRoot "node_modules"))) {
    pnpm install
}
pnpm dev
