[CmdletBinding()]
param(
    [ValidateSet('x64', 'arm64')][string]$Architecture = 'x64',
    [string]$Python = 'python',
    [string]$OutputRoot = '',
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $OutputRoot) { $OutputRoot = Join-Path $repo 'dist\windows' }
$machine = (& $Python -c "import sysconfig; print(sysconfig.get_platform().lower())").Trim()
$expected = @{ x64 = @('win-amd64'); arm64 = @('win-arm64') }[$Architecture]
if ($machine -notin $expected) {
    throw "Python architecture '$machine' does not match requested $Architecture"
}
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw 'pnpm is required to compile the frontend'
}

Push-Location $repo
try {
    & pnpm build
    if ($LASTEXITCODE) { throw 'Frontend build failed' }
    & $Python -m pip install --upgrade ".[windows-package]"
    if ($LASTEXITCODE) { throw 'Could not install project[windows-package]' }

    $localBuild = Join-Path $env:LOCALAPPDATA "RainTechGRC\build\$Architecture"
    $stage = Join-Path $localBuild 'RainTechGRC'
    if ($Clean -and (Test-Path -LiteralPath $localBuild)) {
        Remove-Item -LiteralPath $localBuild -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $localBuild | Out-Null
    $arguments = @(
        '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', 'RainTechGRC',
        '--distpath', $localBuild,
        '--workpath', (Join-Path $localBuild 'work'),
        '--specpath', (Join-Path $localBuild 'spec'),
        '--add-data', "$repo\dist;dist",
        '--add-data', "$repo\catalog\versions;catalog\versions",
        '--add-data', "$repo\docs\templates\hipaa\v2;docs\templates\hipaa\v2",
        '--add-data', "$repo\migrations;migrations",
        '--add-data', "$repo\alembic.ini;.",
        '--collect-all', 'alembic',
        (Join-Path $repo 'api\windows_launcher.py')
    )
    & $Python -m PyInstaller @arguments
    if ($LASTEXITCODE) { throw 'PyInstaller failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $stage 'RainTechGRC.exe'))) {
        throw 'RainTechGRC.exe was not produced'
    }
    $recoveryArguments = @(
        '--noconfirm', '--clean', '--onefile', '--console',
        '--name', 'RainTechGRCRecovery',
        '--distpath', $stage,
        '--workpath', (Join-Path $localBuild 'recovery-work'),
        '--specpath', (Join-Path $localBuild 'recovery-spec'),
        (Join-Path $repo 'api\recovery.py')
    )
    & $Python -m PyInstaller @recoveryArguments
    if ($LASTEXITCODE) { throw 'Recovery-tool packaging failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $stage 'RainTechGRCRecovery.exe'))) {
        throw 'RainTechGRCRecovery.exe was not produced'
    }
}
finally {
    Pop-Location
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$output = (Resolve-Path -LiteralPath $OutputRoot).Path
$zip = Join-Path $output "RainTechGRC-windows-$Architecture.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash | Set-Content -LiteralPath "$zip.sha256"
Write-Output $zip
