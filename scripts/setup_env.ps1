param(
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
}

$pythonExe = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "未找到虚拟环境 Python：$pythonExe"
}

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r requirements.txt

if ($RunTests) {
    & $pythonExe -m unittest discover -s tests -p "test_*.py"
}

Write-Output "环境准备完成。"
Write-Output "使用方式："
Write-Output "  .\\.venv\\Scripts\\python.exe run.py --mode sim"
