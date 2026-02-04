Set-Location -Path $PSScriptRoot

# Optional: activate venv if exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  . .\.venv\Scripts\Activate.ps1
}

$pidFile = Join-Path $PSScriptRoot 'data\uvicorn.pid'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $pidFile) | Out-Null

if (Test-Path $pidFile) {
  $existingPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if ($existingPid) {
    $p = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($p) {
      Write-Host "Server already running (PID=$existingPid)" -ForegroundColor Yellow
      exit 0
    }
  }
}

$pythonExe = (Get-Command python -ErrorAction Stop).Source

$proc = Start-Process -PassThru -FilePath $pythonExe -ArgumentList @(
  '-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000'
) -WorkingDirectory $PSScriptRoot

Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
Write-Host "Started server (PID=$($proc.Id)) at http://127.0.0.1:8000" -ForegroundColor Green
