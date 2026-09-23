[CmdletBinding()]
param(
    [string]$Package = '',
    [int]$Port = 18537
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $Package) {
    $Package = Join-Path $PSScriptRoot '..\..\dist\windows\RainTechGRC-windows-arm64.zip'
}

$packagePath = (Resolve-Path -LiteralPath $Package).Path
$expectedSha256 = '0A0030640906E3683D29642B7761310509FCABC4FEADBC92F9430CF9D69C8913'
$actualSha256 = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash
if ($actualSha256 -ne $expectedSha256) {
    throw "Package hash mismatch; expected final ARM64 ZIP $expectedSha256, got $actualSha256"
}
if ($Port -eq 18433) { throw 'Port 18433 is reserved for the live acceptance application' }
if (@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -gt 0) {
    throw "Port $Port is already in use; choose a free isolated port"
}

$work = Join-Path ([IO.Path]::GetTempPath()) ('raintech-resilience-' + [guid]::NewGuid())
$savedEnvironment = @{
    RAINTECH_DATA_DIR = [Environment]::GetEnvironmentVariable('RAINTECH_DATA_DIR', 'Process')
    RAINTECH_NO_BROWSER = [Environment]::GetEnvironmentVariable('RAINTECH_NO_BROWSER', 'Process')
    RAINTECH_PORT = [Environment]::GetEnvironmentVariable('RAINTECH_PORT', 'Process')
}
$launched = [Collections.Generic.List[Diagnostics.Process]]::new()

function Get-PortListeners {
    foreach ($line in @(netstat.exe -ano -p tcp)) {
        if ($line -match "^\s*TCP\s+(?:\[[^\]]+\]|[^:\s]+):$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            [pscustomobject]@{ OwningProcess = [int]$Matches[1]; Entry = $line.Trim() }
        }
    }
}

function Wait-ForHealth {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 1
            if ($health.status -eq 'ok') { return }
        }
        catch { }
    }
    throw "Application did not become healthy on isolated port $Port"
}

function Stop-ProcessTree {
    param([Diagnostics.Process]$Process)
    try {
        $current = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
        if ($current) { Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue }
    }
    catch {
        # Cleanup retries are best effort; the isolated listener is checked separately.
    }
}

try {
    New-Item -ItemType Directory -Path $work | Out-Null
    Expand-Archive -LiteralPath $packagePath -DestinationPath $work
    $exe = Get-ChildItem -LiteralPath $work -Filter RainTechGRC.exe -Recurse | Select-Object -First 1
    if (-not $exe) { throw 'RainTechGRC.exe is missing from the package' }

    $data = Join-Path $work 'isolated-data'
    $env:RAINTECH_DATA_DIR = $data
    $env:RAINTECH_NO_BROWSER = '1'
    $env:RAINTECH_PORT = "$Port"

    $first = Start-Process -FilePath $exe.FullName -WorkingDirectory $exe.DirectoryName -PassThru -WindowStyle Hidden
    $launched.Add($first)
    Wait-ForHealth

    $marker = 'Resilience verification ' + [guid]::NewGuid().ToString('N')
    $body = @{ name = $marker } | ConvertTo-Json
    $created = Invoke-RestMethod -Method Post "http://127.0.0.1:$Port/api/clients" `
        -ContentType 'application/json' -Body $body
    if ($created.name -ne $marker) { throw 'Synthetic marker did not round-trip before forced close' }

    $duplicate = Start-Process -FilePath $exe.FullName -WorkingDirectory $exe.DirectoryName `
        -PassThru -WindowStyle Hidden
    $launched.Add($duplicate)
    Start-Sleep -Seconds 2

    $listeners = @(Get-PortListeners)
    $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($listeners.Count -eq 0 -or $owners.Count -ne 1 -or $owners[0] -ne $first.Id) {
        throw "Duplicate launch changed the isolated listener ownership; listeners: $($owners -join ', ')"
    }
    $null = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2

    Stop-ProcessTree $duplicate
    Stop-ProcessTree $first
    foreach ($listener in @(Get-PortListeners)) {
        if ($listener.OwningProcess -in @($first.Id, $duplicate.Id)) {
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    $launched.Clear()
    for ($attempt = 0; $attempt -lt 20 -and @(Get-PortListeners).Count -gt 0; $attempt++) {
        Start-Sleep -Milliseconds 250
    }
    if (@(Get-PortListeners).Count -gt 0) { throw 'Listener remained after forced application close' }

    $restart = Start-Process -FilePath $exe.FullName -WorkingDirectory $exe.DirectoryName `
        -PassThru -WindowStyle Hidden
    $launched.Add($restart)
    Wait-ForHealth
    $clients = Invoke-RestMethod "http://127.0.0.1:$Port/api/clients"
    if ($marker -notin @($clients.name)) { throw 'Synthetic marker did not survive forced close and restart' }

    [pscustomobject]@{
        PackageSha256 = $actualSha256
        IsolatedPort = $Port
        DuplicateLaunch = 'No conflicting listener; original process remained healthy'
        ForcedClose = 'Listener released'
        RestartPersistence = 'Synthetic marker retained'
        Marker = $marker
        DataRoot = $data
    } | Format-List
}
finally {
    $ownedIds = @($launched | ForEach-Object { $_.Id })
    foreach ($process in $launched) {
        try { Stop-ProcessTree $process } catch { }
    }
    foreach ($listener in @(Get-PortListeners)) {
        if ($listener.OwningProcess -in $ownedIds) {
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
}
