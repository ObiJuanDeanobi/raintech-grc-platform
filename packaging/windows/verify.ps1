[CmdletBinding()]
param([Parameter(Mandatory)][string]$Package, [int]$Port = 18432)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$packagePath = (Resolve-Path -LiteralPath $Package).Path
$work = Join-Path ([IO.Path]::GetTempPath()) ('raintech-verify-' + [guid]::NewGuid())
New-Item -ItemType Directory -Force -Path $work | Out-Null

function Wait-ForHealth {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 1
            if ($health.status -eq 'ok') { return }
        }
        catch { }
    }
    throw 'Application did not become healthy'
}

function Stop-App {
    param([Diagnostics.Process]$Process)
    try {
        Invoke-RestMethod -Method Post "http://127.0.0.1:$Port/api/app/shutdown" -TimeoutSec 2 | Out-Null
        [void]$Process.WaitForExit(10000)
    }
    catch { }
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force }
}

try {
    Expand-Archive -LiteralPath $packagePath -DestinationPath $work -Force
    $exe = Get-ChildItem -LiteralPath $work -Filter RainTechGRC.exe -Recurse | Select-Object -First 1
    if (-not $exe) { throw 'RainTechGRC.exe is missing' }
    $data = Join-Path $work 'isolated-data'
    $env:RAINTECH_DATA_DIR = $data
    $env:RAINTECH_NO_BROWSER = '1'
    $env:RAINTECH_PORT = "$Port"
    $signature = Get-AuthenticodeSignature -LiteralPath $exe.FullName
    if ($signature.Status -notin @('Valid', 'NotSigned')) {
        throw "Unexpected signature status: $($signature.Status)"
    }

    $first = Start-Process -FilePath $exe.FullName -WorkingDirectory $exe.DirectoryName -PassThru -WindowStyle Hidden
    try {
        $coldWatch = [Diagnostics.Stopwatch]::StartNew()
        Wait-ForHealth
        $coldWatch.Stop()
        $ui = Invoke-WebRequest "http://127.0.0.1:$Port/" -UseBasicParsing
        if ($ui.StatusCode -ne 200 -or $ui.Content -notmatch '<div id="root"></div>') {
            throw 'Compiled browser UI did not load'
        }
        $marker = 'Windows package ' + [guid]::NewGuid().ToString('N')
        $body = @{ name = $marker } | ConvertTo-Json
        $created = Invoke-RestMethod -Method Post "http://127.0.0.1:$Port/api/clients" -ContentType 'application/json' -Body $body
        if ($created.name -ne $marker) { throw 'Synthetic client write did not round-trip' }
        if (-not (Test-Path -LiteralPath (Join-Path $data 'workspace.db'))) {
            throw 'The database was not written to the isolated data directory'
        }
    }
    finally { Stop-App $first }

    $second = Start-Process -FilePath $exe.FullName -WorkingDirectory $exe.DirectoryName -PassThru -WindowStyle Hidden
    try {
        $restartWatch = [Diagnostics.Stopwatch]::StartNew()
        Wait-ForHealth
        $restartWatch.Stop()
        $clients = Invoke-RestMethod "http://127.0.0.1:$Port/api/clients"
        if ($marker -notin @($clients.name)) { throw 'Synthetic client did not survive restart' }
        $connections = Get-NetTCPConnection -OwningProcess $second.Id -ErrorAction SilentlyContinue
        $remote = @($connections | Where-Object {
            $_.RemoteAddress -and $_.RemoteAddress -notin @('127.0.0.1', '::1', '0.0.0.0', '::')
        })
        if ($remote.Count -gt 0) { throw 'A non-loopback connection was detected' }
    }
    finally { Stop-App $second }

    $peBytes = [IO.File]::ReadAllBytes($exe.FullName)
    $peOffset = [BitConverter]::ToInt32($peBytes, 0x3c)
    $machine = [BitConverter]::ToUInt16($peBytes, $peOffset + 4)
    $architecture = switch ($machine) {
        0xAA64 { 'ARM64' }
        0x8664 { 'x64' }
        default { "Unknown (0x{0:X4})" -f $machine }
    }
    [pscustomobject]@{
        Package = $packagePath
        Architecture = $architecture
        PackageMiB = [math]::Round((Get-Item -LiteralPath $packagePath).Length / 1MB, 1)
        ColdLaunchMs = $coldWatch.ElapsedMilliseconds
        RestartMs = $restartWatch.ElapsedMilliseconds
        Signature = $signature.Status
        DataPath = $data
        PersistedMarker = $marker
        NonLoopbackConnections = 0
    } | Format-List
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item Env:RAINTECH_DATA_DIR, Env:RAINTECH_NO_BROWSER, Env:RAINTECH_PORT -ErrorAction SilentlyContinue
}
