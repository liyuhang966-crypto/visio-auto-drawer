param([string]$ProjectRoot = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { $Python = 'python' }
& $Python (Join-Path $PSScriptRoot 'test_visio_com.py') --project-root $ProjectRoot
if ($LASTEXITCODE -ne 0) { throw 'Visio COM check failed.' }
