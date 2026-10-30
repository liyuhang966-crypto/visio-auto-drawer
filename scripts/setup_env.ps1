param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvRoot = Join-Path $RepoRoot '.venv'
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw 'Unable to create Python virtual environment.' }
$VenvPython = Join-Path $VenvRoot 'Scripts/python.exe'
& $VenvPython -m pip install -r (Join-Path $RepoRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Output 'Environment ready. Run scripts/run_test.ps1 to check Visio COM.'
