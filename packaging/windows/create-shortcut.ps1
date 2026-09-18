[CmdletBinding()]
param([string]$PackageRoot = '', [string]$Name = 'RainTech GRC')
$ErrorActionPreference = 'Stop'; Set-StrictMode -Version Latest
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $PackageRoot) { $PackageRoot = Join-Path $repo 'dist\windows\RainTechGRC' }
$root = (Resolve-Path $PackageRoot).Path; $desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = Join-Path $desktop "$Name.lnk"; $shell = New-Object -ComObject WScript.Shell; $link = $shell.CreateShortcut($shortcut)
$link.TargetPath = Join-Path $root 'RainTechGRC.exe'; if(-not (Test-Path $link.TargetPath)){throw 'RainTechGRC.exe not found'}; $link.WorkingDirectory = $root; $link.Save()
Write-Output "Created $shortcut"
