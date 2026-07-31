param(
    [ValidateSet("arm64", "x64")]
    [string]$Architecture = "arm64"
)

$ErrorActionPreference = "Stop"

$Executable = Join-Path $env:LOCALAPPDATA "RainTech\PackageSpike\out\$Architecture\RainTechGRCSpike\RainTechGRCSpike.exe"
$Health = "http://127.0.0.1:18432/api/health"
$Clients = "http://127.0.0.1:18432/api/clients"

if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Build the spike before verifying it: $Executable"
}

function Wait-ForHealth {
    param([int]$TimeoutSeconds = 30)
    $watch = [Diagnostics.Stopwatch]::StartNew()
    while ($watch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-RestMethod -Uri $Health -TimeoutSec 1
            if ($response.status -eq "ok") { return $watch.Elapsed.TotalMilliseconds }
        }
        catch {
            Start-Sleep -Milliseconds 100
        }
    }
    throw "Packaged app did not become healthy within $TimeoutSeconds seconds"
}

function Stop-Spike {
    param([switch]$Force)
    if (-not $Force) {
        try {
            Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:18432/api/app/shutdown" -TimeoutSec 2 | Out-Null
            Start-Sleep -Milliseconds 500
        }
        catch { }
    }
    Get-Process -Name "RainTechGRCSpike" -ErrorAction SilentlyContinue | Stop-Process -Force
}

Stop-Spike -Force
$first = Start-Process -FilePath $Executable -PassThru
try {
    $coldMs = Wait-ForHealth
    $marker = "Package spike " + [Guid]::NewGuid().ToString("N")
    $created = Invoke-RestMethod -Method Post -Uri $Clients -ContentType "application/json" -Body (@{ name = $marker } | ConvertTo-Json)
    if ($created.name -ne $marker) { throw "Client write did not round-trip" }

    Stop-Spike -Force
    $restart = Start-Process -FilePath $Executable -PassThru
    $restartMs = Wait-ForHealth
    $saved = Invoke-RestMethod -Uri $Clients
    if ($saved.name -notcontains $marker) { throw "SQLite write did not survive forced close and restart" }

    $connections = Get-NetTCPConnection -OwningProcess $restart.Id -ErrorAction SilentlyContinue
    $nonLoopback = @($connections | Where-Object {
        $_.RemoteAddress -and $_.RemoteAddress -notin @("0.0.0.0", "::", "127.0.0.1", "::1")
    })
    if ($nonLoopback.Count -gt 0) { throw "Packaged app opened a non-loopback connection" }

    $package = Get-ChildItem -LiteralPath (Split-Path -Parent $Executable) -Recurse -File
    $bytes = ($package | Measure-Object -Property Length -Sum).Sum
    $peBytes = [IO.File]::ReadAllBytes($Executable)
    $peOffset = [BitConverter]::ToInt32($peBytes, 0x3c)
    $peMachine = [BitConverter]::ToUInt16($peBytes, $peOffset + 4)
    $packageArchitecture = switch ($peMachine) {
        0xAA64 { "ARM64" }
        0x8664 { "x64" }
        default { "Unknown (0x{0:X4})" -f $peMachine }
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $Executable
    $dataPath = Join-Path $env:LOCALAPPDATA "RainTech\GRC Platform Spike\workspace.db"
    if (-not (Test-Path -LiteralPath $dataPath)) { throw "Expected user-writable SQLite database is missing" }

    [pscustomobject]@{
        Executable = $Executable
        HostArchitecture = $env:PROCESSOR_ARCHITECTURE
        PackageArchitecture = $packageArchitecture
        ColdLaunchMs = [math]::Round($coldMs)
        RestartMs = [math]::Round($restartMs)
        PackageMiB = [math]::Round($bytes / 1MB, 1)
        SignatureStatus = $signature.Status
        DataPath = $dataPath
        PersistedMarker = $marker
        NonLoopbackConnections = $nonLoopback.Count
    } | Format-List
}
finally {
    Stop-Spike
}
