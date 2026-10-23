param([switch]$ImportRegions)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) { throw '.venv is missing. Create it and install backend requirements first.' }
$env:PYTHONPATH = Join-Path $Root 'backend'
$env:LOCAL_DATABASE_SSLMODE = 'disable'
& $venvPython (Join-Path $Root 'backend\scripts\bootstrap_local_postgis.py')
if ($LASTEXITCODE -ne 0) { throw 'Local PostGIS bootstrap failed.' }
if ($ImportRegions) {
  $env:DATABASE_URL = $env:LOCAL_DATABASE_URL
  $env:DATABASE_SSLMODE = 'disable'
  & $venvPython (Join-Path $Root 'backend\scripts\supabase_io.py') import-regions
  if ($LASTEXITCODE -ne 0) { throw 'Region import failed.' }
}
Write-Host 'Local PostGIS setup completed. Import graph snapshots separately when required.'
