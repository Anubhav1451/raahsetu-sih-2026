param(
    [switch]$Once = $true,
    [switch]$Loop,
    [int]$IntervalMinutes = 60,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$script = Join-Path $projectRoot "scripts\scheduled_refresh.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing. Run scripts/setup.ps1 first."
}

$argsList = @($script)
if ($Loop) {
    $argsList += "--loop"
    $argsList += "--interval-minutes"
    $argsList += $IntervalMinutes
} else {
    $argsList += "--once"
}
if ($DryRun) {
    $argsList += "--dry-run"
}

Write-Host "Running RaahSetu scheduled data refresh automation..." -ForegroundColor Cyan
& $python $argsList
if ($LASTEXITCODE -ne 0) {
    throw "Scheduled data refresh failed with exit code $LASTEXITCODE"
}
