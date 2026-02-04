Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$teamRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $teamRoot

$toolsVenv = Join-Path $teamRoot '.venv-tools'
$py = Join-Path $toolsVenv 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $py)) {
  Write-Host 'Creating tools venv (.venv-tools)...'
  python -m venv $toolsVenv
}

Write-Host 'Installing tools dependencies...'
& $py -m pip install --upgrade pip
& $py -m pip install -r (Join-Path $teamRoot 'כלים\requirements.txt')

$env:TALMID_PYTHON = $py
Write-Host 'Running full tools pipeline (updates מידע_חשוב.md)...'
& (Join-Path $teamRoot 'כלים\run_all.ps1')

Write-Host 'Refresh data OK' -ForegroundColor Green
