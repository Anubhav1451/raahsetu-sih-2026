# Supabase backup and restore

Create a custom-format backup without committing it:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_supabase.ps1
```

Restore into a local PostgreSQL/PostGIS database:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore_postgres.ps1 -DumpFile work\backups\supabase-YYYYMMDD-HHMMSS.dump -TargetDatabaseUrl $env:LOCAL_DATABASE_URL
```

Validate table counts, migration status, source hashes and route smoke tests before removing any large Supabase table. Never put a service-role key, password or dump file in Git. The backup scripts read credentials from environment variables and do not print them.
