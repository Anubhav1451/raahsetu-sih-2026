$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$ruff = Join-Path $projectRoot ".venv\Scripts\ruff.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing. Run scripts/setup.ps1 first."
}

Push-Location $projectRoot
try {
    & $python -m pytest backend\tests -q
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }

    & $ruff check backend scripts
    if ($LASTEXITCODE -ne 0) { throw "Python quality checks failed." }

    & $python backend\scripts\evaluate.py
    if ($LASTEXITCODE -ne 0) { throw "Routing evaluation failed." }

    & $python scripts\audit_data.py
    if ($LASTEXITCODE -ne 0) { throw "Dataset integrity audit failed." }

    & $python scripts\validate_deployment.py
    if ($LASTEXITCODE -ne 0) { throw "Deployment contract validation failed." }

    Push-Location frontend
    try {
        & node test-sw-security.cjs
        if ($LASTEXITCODE -ne 0) { throw "Service worker security checks failed." }

        & node test-pwa.cjs
        if ($LASTEXITCODE -ne 0) { throw "PWA contract checks failed." }

        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
    }
    finally {
        Pop-Location
    }

    Write-Host "RaahSetu local verification completed successfully." -ForegroundColor Green
}
finally {
    Pop-Location
}
