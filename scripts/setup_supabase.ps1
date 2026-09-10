$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$PythonPath = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

Push-Location $ProjectRoot
try {
    & $PythonPath backend/scripts/supabase_io.py apply-migration supabase/migrations/001_spatial_foundation.sql
    if ($LASTEXITCODE -ne 0) { throw 'Spatial migration failed.' }
    & $PythonPath backend/scripts/supabase_io.py apply-migration supabase/migrations/002_operations_foundation.sql
    if ($LASTEXITCODE -ne 0) { throw 'Operations migration failed.' }
    & $PythonPath backend/scripts/supabase_io.py apply-migration supabase/migrations/003_auth_and_review.sql
    if ($LASTEXITCODE -ne 0) { throw 'Auth and review migration failed.' }
    & $PythonPath backend/scripts/supabase_io.py apply-migration supabase/migrations/004_fleet_tracking.sql
    if ($LASTEXITCODE -ne 0) { throw 'Fleet tracking migration failed.' }
    & $PythonPath backend/scripts/supabase_io.py apply-migration supabase/migrations/005_alert_generation.sql
    if ($LASTEXITCODE -ne 0) { throw 'Alert migration failed.' }
    & $PythonPath backend/scripts/supabase_io.py apply-migration supabase/migrations/006_report_credibility.sql
    if ($LASTEXITCODE -ne 0) { throw 'Report credibility migration failed.' }
    & $PythonPath backend/scripts/supabase_io.py import-regions datasets/processed/ne-coverage-catalog.json
    if ($LASTEXITCODE -ne 0) { throw 'Region catalog import failed.' }
    & $PythonPath backend/scripts/supabase_io.py status
    if ($LASTEXITCODE -ne 0) { throw 'Database status check failed.' }
    Write-Host 'Supabase foundation is ready.'
} finally {
    Pop-Location
}
