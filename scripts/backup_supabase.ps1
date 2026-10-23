param(
    [string]$OutputDirectory = "work\backups"
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PgDump = (Get-Command pg_dump -ErrorAction SilentlyContinue).Source
if (-not $PgDump -and (Test-Path 'D:\POSTGRESQL\bin\pg_dump.exe')) { $PgDump = 'D:\POSTGRESQL\bin\pg_dump.exe' }
if (-not $PgDump) { throw 'pg_dump is required. Install PostgreSQL client tools first.' }
$envFile = Join-Path $Root '.env'
if (-not (Test-Path $envFile)) { throw '.env is missing.' }
$databaseUrl = (Get-Content $envFile | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1) -replace '^DATABASE_URL=', ''
if (-not $databaseUrl) { throw 'DATABASE_URL is missing from .env.' }
$dir = Join-Path $Root $OutputDirectory
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$target = Join-Path $dir "supabase-$stamp.dump"
# Include the auth schema so Supabase user accounts survive a restore;
# service-managed schemas (realtime, storage internals) are left to the platform.
& $PgDump --format=custom --no-owner --no-acl --schema=public --schema=auth --dbname=$databaseUrl --file=$target
if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed.' }
if ((Get-Item $target).Length -eq 0) { throw 'pg_dump produced an empty file; not a valid backup.' }
Write-Host "Backup created: $target ($([math]::Round((Get-Item $target).Length / 1MB, 1)) MB)"
