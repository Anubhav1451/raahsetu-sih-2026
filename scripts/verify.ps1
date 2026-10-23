$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$ruff = Join-Path $projectRoot ".venv\Scripts\ruff.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment is missing. Run scripts/setup.ps1 first."
}

Push-Location $projectRoot
try {
    # Tests import the backend "app" package, so pytest must run from backend/.
    Push-Location (Join-Path $projectRoot "backend")
    try {
        & $python -m pytest tests -q
    }
    finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }

    & $ruff check backend scripts
    if ($LASTEXITCODE -ne 0) { throw "Python quality checks failed." }

    # evaluate.py imports the backend "app" package; run it from backend/ with
    # the package on PYTHONPATH because Python puts the script's own dir first.
    Push-Location (Join-Path $projectRoot "backend")
    try {
        $env:PYTHONPATH = "."
        try {
            & $python scripts\evaluate.py
        }
        finally {
            Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
        }
    }
    finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { throw "Routing evaluation failed." }

    & $python scripts\audit_data.py
    if ($LASTEXITCODE -ne 0) { throw "Dataset integrity audit failed." }

    Push-Location frontend
    try {
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
