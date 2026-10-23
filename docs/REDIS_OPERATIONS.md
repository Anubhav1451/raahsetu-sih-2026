# Redis operations

Redis is an acceleration and event-delivery layer. PostgreSQL/PostGIS remains
the source of truth for closures, approvals, evidence, routes and labels.

## Local persistent startup

```powershell
docker compose -f docker-compose.redis.yml up -d
$env:REDIS_URL = "redis://localhost:6379/0"
```

The compose file enables Redis AOF persistence and a named Docker volume. The
volume survives container restarts; it is not a substitute for database backups.

## Durable telemetry worker

```powershell
..\.venv\Scripts\python.exe backend/scripts/consume_telemetry_stream.py --once
```

The worker uses consumer group `raahsetu-ops`, acknowledges only successfully
handled events, and is safe to replay when downstream handling is idempotent.

## Production security

Use a managed Redis service or a private network, TLS (`rediss://`), ACL user,
and a secret-managed URL. Do not commit credentials. Set a bounded memory policy
for ephemeral keys and monitor stream length, pending entries, hit rate, and
connection errors. Never place approval decisions or authoritative closures only
in Redis.
