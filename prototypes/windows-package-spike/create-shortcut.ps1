$ErrorActionPreference = "Stop"

$Executable = Join-Path $env:LOCALAPPDATA "RainTech\PackageSpike\out\arm64\RainTechGRCSpike\RainTechGRCSpike.exe"
if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Build the spike before creating its shortcut: $Executable"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "RainTech GRC Spike.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Executable
$Shortcut.WorkingDirectory = Split-Path -Parent $Executable
$Shortcut.Description = "Throwaway RainTech GRC Windows package spike"
$Shortcut.Save()

Write-Host "Created: $ShortcutPath"
