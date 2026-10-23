param(
    [Parameter(Mandatory=$true)][string]$DumpFile,
    [string]$TargetDatabaseUrl = ''
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PgRestore = (Get-Command pg_restore -ErrorAction SilentlyContinue).Source
if (-not $PgRestore -and (Test-Path 'D:\POSTGRESQL\bin\pg_restore.exe')) { $PgRestore = 'D:\POSTGRESQL\bin\pg_restore.exe' }
if (-not $PgRestore) { throw 'pg_restore is required. Install PostgreSQL client tools first.' }
if (-not [IO.Path]::IsPathRooted($DumpFile)) { $DumpFile = Join-Path $Root $DumpFile }
if (-not (Test-Path $DumpFile)) { throw "Dump file not found: $DumpFile" }
if (-not $TargetDatabaseUrl) {
    $envFile = Join-Path $Root '.env'
    $TargetDatabaseUrl = (Get-Content $envFile | Where-Object { $_ -match '^LOCAL_DATABASE_URL=' } | Select-Object -First 1) -replace '^LOCAL_DATABASE_URL=', ''
}
if (-not $TargetDatabaseUrl) { throw 'Pass -TargetDatabaseUrl or set LOCAL_DATABASE_URL in .env.' }
& $PgRestore --clean --if-exists --no-owner --no-acl --dbname=$TargetDatabaseUrl $DumpFile
if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed.' }
Write-Host "Restore completed into the selected local PostgreSQL database."
