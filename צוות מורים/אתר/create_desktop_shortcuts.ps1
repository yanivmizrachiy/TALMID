Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$siteRoot = $PSScriptRoot
$openScript = Join-Path $siteRoot 'open_talmid.ps1'
$stopScript = Join-Path $siteRoot 'stop.ps1'

if (-not (Test-Path -LiteralPath $openScript)) {
  throw "Missing script: $openScript"
}
if (-not (Test-Path -LiteralPath $stopScript)) {
  throw "Missing script: $stopScript"
}

function Get-ShellPowerShellExe {
  $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
  if ($pwsh) { return $pwsh.Source }
  $ps = Get-Command powershell -ErrorAction SilentlyContinue
  if ($ps) { return $ps.Source }
  return 'powershell.exe'
}

$desktop = [Environment]::GetFolderPath('Desktop')
if (-not $desktop) {
  throw 'Could not resolve Desktop folder path.'
}

$psExe = Get-ShellPowerShellExe

function New-DesktopShortcut {
  param(
    [Parameter(Mandatory=$true)][string]$LinkName,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string]$IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
  )

  $linkPath = Join-Path $desktop $LinkName

  $wsh = New-Object -ComObject WScript.Shell
  $lnk = $wsh.CreateShortcut($linkPath)
  $lnk.TargetPath = $psExe
  $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
  $lnk.WorkingDirectory = $siteRoot
  $lnk.WindowStyle = 1
  $lnk.IconLocation = $IconLocation
  $lnk.Description = 'TALMID'
  $lnk.Save()

  Write-Host "Created: $linkPath" -ForegroundColor Green
}

New-DesktopShortcut -LinkName 'TALMID - אתר.lnk' -ScriptPath $openScript -IconLocation "$env:SystemRoot\System32\shell32.dll,220"
New-DesktopShortcut -LinkName 'TALMID - עצירה.lnk' -ScriptPath $stopScript -IconLocation "$env:SystemRoot\System32\shell32.dll,131"

Write-Host 'Desktop shortcuts ready.' -ForegroundColor Green
