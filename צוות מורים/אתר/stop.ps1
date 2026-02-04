Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location -Path $PSScriptRoot

$pidFile = Join-Path $PSScriptRoot 'data\uvicorn.pid'
if (-not (Test-Path $pidFile)) {
  Write-Host 'No PID file found. Server may not be running.' -ForegroundColor Yellow
  exit 0
}

$pid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $pid) {
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  Write-Host 'PID file empty. Cleaned.' -ForegroundColor Yellow
  exit 0
}

$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if ($proc) {
  Stop-Process -Id $pid -Force
  Write-Host "Stopped server (PID=$pid)" -ForegroundColor Green
} else {
  Write-Host "Process not found (PID=$pid). Cleaned." -ForegroundColor Yellow
}

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
