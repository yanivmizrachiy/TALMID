Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$teamRoot = Split-Path -Parent $here

Set-Location -Path $teamRoot

$pythonExe = $env:TALMID_PYTHON
if (-not $pythonExe) {
	$pythonExe = 'python'
}

Write-Host "Using Python: $pythonExe"

function Invoke-PythonScript([string]$scriptName) {
	$scriptPath = Join-Path -Path $here -ChildPath $scriptName
	if (-not (Test-Path -LiteralPath $scriptPath)) {
		throw "Missing script: $scriptPath"
	}
	Write-Host "Running: $scriptName"
	& $pythonExe $scriptPath
}

Invoke-PythonScript 'generate_homerooms.py'
Invoke-PythonScript 'generate_structure.py'
Invoke-PythonScript 'import_excel_students.py'
Invoke-PythonScript 'generate_manual_group_students.py'
Invoke-PythonScript 'generate_reports.py'
Invoke-PythonScript 'generate_summary.py'
Invoke-PythonScript 'generate_updates.py'
Invoke-PythonScript 'validate_data.py'

Write-Host "DONE"
