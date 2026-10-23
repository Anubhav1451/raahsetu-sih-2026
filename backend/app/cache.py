"""Optional Redis cache with a safe in-process fallback.

Redis accelerates ephemeral data only. PostgreSQL/PostGIS remains the source
of truth for routes, closures, evidence and audit records.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

_local: dict[str, tuple[float, str]] = {}
_redis = None
_logger = logging.getLogger("raahsetu.cache")


def _client():
    global _redis
    if _redis is not None:
        return _redis
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=1)
        client.ping()
        _redis = client
        return client
    except Exception as exc:  # noqa: BLE001 - optional Redis must never be fatal
        _logger.debug("Redis unavailable: %s", exc)
        return None


def cache_get(key: str) -> Any | None:
    client = _client()
    if client is not None:
        try:
            raw = client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as exc:  # noqa: BLE001 - fallback on any client failure
            _logger.debug("Redis GET failed; using local fallback: %s", exc)
    item = _local.get(key)
    if not item or item[0] <= time.time():
        _local.pop(key, None)
        return None
    return json.loads(item[1])


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    payload = json.dumps(value, default=str, separators=(",", ":"))
    client = _client()
    if client is not None:
        try:
            client.setex(key, ttl_seconds, payload)
            return
        except Exception as exc:  # noqa: BLE001 - fallback on any client failure
            _logger.debug("Redis SETEX failed; using local fallback: %s", exc)
    _local[key] = (time.time() + ttl_seconds, payload)


def cache_clear() -> None:
    _local.clear()


def stream_add(stream: str, fields: dict[str, Any], maxlen: int = 10_000) -> str | None:
    """Append an ephemeral event to a Redis Stream when Redis is configured.

    The event bus is intentionally best-effort: PostgreSQL remains authoritative,
    and a Redis outage must never reject an already persisted telemetry event.
    """
    client = _client()
    if client is None:
        return None
    try:
        encoded = {key: json.dumps(value, default=str) for key, value in fields.items()}
        return str(client.xadd(stream, encoded, maxlen=maxlen, approximate=True))
    except Exception as exc:  # noqa: BLE001 - stream is best-effort
        _logger.debug("Redis stream append failed: %s", exc)
        return None


def stream_read_group(
    stream: str,
    group: str,
    consumer: str,
    count: int = 10,
    block_ms: int = 1000,
) -> list[tuple[str, dict[str, str]]]:
    """Read pending/new events for a durable consumer group, if Redis is live."""
    client = _client()
    if client is None:
        return []
    try:
        try:
            client.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001 - BUSYGROUP is harmless
            _logger.debug("Stream group already exists or could not be created: %s", exc)
        rows = client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block_ms)
        return [(event_id, fields) for _, events in rows for event_id, fields in events]
    except Exception as exc:  # noqa: BLE001 - event bus is best-effort
        _logger.debug("Redis stream read failed: %s", exc)
        return []


def stream_ack(stream: str, group: str, event_ids: list[str]) -> int:
    client = _client()
    if client is None or not event_ids:
        return 0
    try:
        return int(client.xack(stream, group, *event_ids))
    except Exception as exc:  # noqa: BLE001 - event bus is best-effort
        _logger.debug("Redis stream ack failed: %s", exc)
        return 0
def cache_health() -> dict[str, Any]:
    """Return explicit cache/bus status for diagnostics and admin UI."""
    configured = bool(os.getenv("REDIS_URL"))
    client = _client() if configured else None
    if client is None:
        return {
            "configured": configured,
            "backend": "in-memory",
            "reachable": False,
            "authoritative_store": "PostgreSQL/PostGIS",
        }
    try:
        info = client.info(section="server")
        return {
            "configured": True,
            "backend": "redis",
            "reachable": True,
            "redis_version": info.get("redis_version"),
            "authoritative_store": "PostgreSQL/PostGIS",
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics must not break API
        _logger.debug("Redis health check failed: %s", exc)
        return {
            "configured": True,
            "backend": "in-memory",
            "reachable": False,
            "authoritative_store": "PostgreSQL/PostGIS",
        }
