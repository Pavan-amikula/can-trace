$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
}
& '.venv/Scripts/python.exe' -m pip install -e '.[dev]'
& '.venv/Scripts/python.exe' scripts/download_data.py
if ($LASTEXITCODE -ne 0) { throw 'Dataset download or integrity check failed' }
& '.venv/Scripts/python.exe' -m cantrace.evaluate
if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed' }
& '.venv/Scripts/python.exe' -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& '.venv/Scripts/python.exe' -m cantrace.cli serve
