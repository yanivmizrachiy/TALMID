Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$siteRoot = $PSScriptRoot
Set-Location -Path $siteRoot

$setupScript = Join-Path $siteRoot 'setup.ps1'
$runScript = Join-Path $siteRoot 'run.ps1'

# Ensure venv exists (so the site keeps working even after code changes)
$venvPython = Join-Path $siteRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
  if (Test-Path -LiteralPath $setupScript) {
    Write-Host 'Virtualenv missing; running setup...' -ForegroundColor Yellow
    & $setupScript
  }
}

# Start server if not already running
& $runScript

# Wait briefly for server to accept connections
$url = 'http://127.0.0.1:8000/'
for ($i = 0; $i -lt 40; $i++) {
  try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri $url | Out-Null
    break
  } catch {
    Start-Sleep -Milliseconds 250
  }
}

Start-Process $url
