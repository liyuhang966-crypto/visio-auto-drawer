param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$Diagram = 'output/diagram.json',
    [string]$Output = ''
)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { $Python = 'python' }
$Arguments = @((Join-Path $PSScriptRoot 'run_pipeline.py'), '--project-root', $ProjectRoot, '--diagram', $Diagram, '--reference-locked')
if ($Output) { $Arguments += @('--output', $Output) }
& $Python @Arguments
if ($LASTEXITCODE -ne 0) { throw 'Reference drawing or verification did not pass. Review the trace and reports.' }
