"""Small durable consumer for the RaahSetu telemetry stream.

This worker acknowledges an event only after the handler returns successfully.
It is intentionally a safe demo/operations worker; PostgreSQL remains the source
of truth and replaying an event must therefore be idempotent downstream.
"""
from __future__ import annotations

import argparse
import json
import logging
import os

from app.cache import stream_ack, stream_read_group

logger = logging.getLogger("raahsetu.telemetry_worker")


def handle_event(event_id: str, fields: dict[str, str]) -> None:
    logger.info("telemetry event %s: %s", event_id, json.dumps(fields, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="read one batch and exit")
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()
    if not os.getenv("REDIS_URL"):
        logger.error("REDIS_URL is required for the telemetry worker")
        return 2
    while True:
        events = stream_read_group("raahsetu:telemetry", "raahsetu-ops", "worker-1", args.count)
        acknowledged: list[str] = []
        for event_id, fields in events:
            handle_event(event_id, fields)
            acknowledged.append(event_id)
        stream_ack("raahsetu:telemetry", "raahsetu-ops", acknowledged)
        if args.once:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
