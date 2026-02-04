Set-Location -Path $PSScriptRoot

# Create venv if missing
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"

# Upgrade pip + install deps
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

Write-Host "Setup OK" -ForegroundColor Green
