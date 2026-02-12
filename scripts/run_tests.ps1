$ErrorActionPreference = "Stop"

Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

$pythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

& $pythonExe -m unittest discover -s tests -p "test_*.py"
