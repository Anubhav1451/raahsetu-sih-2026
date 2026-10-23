"""Automated scheduled data refresh runner for RaahSetu.

Periodically:
1. Refreshes live weather cache from Open-Meteo for all 8 Northeast station locations.
2. Ingests official early warning feeds (NDMA SACHET, CWC, Highway Traffic).
3. Verifies local dataset integrity and updates datasets/DATA_STATUS.json.
4. Records auditable import/refresh run into PostGIS data_import_runs table if DATABASE_URL is set.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

# Add backend directory to sys.path so app package can be imported
ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("raahsetu.scheduled_refresh")

STATUS_FILE = ROOT / "datasets" / "DATA_STATUS.json"


def refresh_weather_cache() -> list[dict]:
    """Refresh live weather predictions for all 8 Northeast reference stations."""
    from app.weather import get_all_live_weather

    logger.info("Polling live weather from Open-Meteo for 8 NE stations...")
    weather = get_all_live_weather()
    logger.info("Retrieved weather data for %d stations.", len(weather))
    return weather


def check_official_feeds() -> tuple[list, list]:
    """Check status of official early-warning feeds."""
    from app.live_ingestion import get_official_feeds_status, ingest_live_official_advisories

    logger.info("Checking official live feed adapters...")
    status = get_official_feeds_status()
    advisories = ingest_live_official_advisories()
    for s in status:
        logger.info("  Feed: %s [%s] - %s", s.source_name, s.status, s.coverage)
    logger.info("Active advisories ingested: %d", len(advisories))
    return status, advisories


def update_data_status(weather_count: int, advisory_count: int, dry_run: bool = False) -> dict:
    """Update datasets/DATA_STATUS.json with fresh audit metadata."""
    now_iso = datetime.now(UTC).isoformat()
    current_status = {}
    if STATUS_FILE.exists():
        try:
            current_status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            current_status = {}

    current_status["last_scheduled_refresh"] = now_iso
    current_status["weather_stations_live"] = weather_count
    current_status["active_early_warning_advisories"] = advisory_count

    if not dry_run:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps(current_status, indent=2), encoding="utf-8")
        logger.info("Updated status metadata in %s", STATUS_FILE)

    return current_status


def record_import_run_in_postgis(weather_count: int, advisory_count: int) -> None:
    """If PostGIS is configured, log an immutable run record into data_import_runs."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.info("DATABASE_URL not set; skipping remote database import run logging.")
        return

    try:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(db_url, sslmode=os.getenv("DATABASE_SSLMODE", "require")) as conn:
            conn.execute(
                """update data_source_registry
                set last_imported_at=now(), updated_at=now(), record_count=%s
                where source_id='open-meteo'""",
                (weather_count,),
            )
            conn.execute(
                """insert into data_import_runs
                (source_id, dataset_version, completed_at, status, records_seen, metadata)
                values(%s, %s, now(), 'succeeded', %s, %s)""",
                (
                    "open-meteo",
                    datetime.now(UTC).strftime("%Y%m%d%H%M"),
                    weather_count + advisory_count,
                    Jsonb({
                        "weather_stations": weather_count,
                        "advisories": advisory_count,
                        "triggered_by": "scheduled_refresh.py",
                    }),
                ),
            )
            logger.info("Logged successful scheduled import run to Supabase data_import_runs.")
    except Exception as exc:
        logger.warning("Failed to log run to database: %s", exc)


def run_refresh_cycle(dry_run: bool = False) -> dict:
    """Execute a single data refresh and audit cycle."""
    logger.info("=== Starting RaahSetu Scheduled Data Refresh Cycle ===")
    weather = refresh_weather_cache()
    feeds_status, advisories = check_official_feeds()
    update_data_status(len(weather), len(advisories), dry_run=dry_run)
    if not dry_run:
        record_import_run_in_postgis(len(weather), len(advisories))
    logger.info("=== Refresh Cycle Completed Successfully ===")
    return {
        "refreshed_at": datetime.now(UTC).isoformat(),
        "weather_stations": len(weather),
        "active_advisories": len(advisories),
    }


def main():
    parser = argparse.ArgumentParser(description="RaahSetu Scheduled Data Refresh Automation Runner")
    parser.add_argument("--once", action="store_true", help="Run once and exit immediately")
    parser.add_argument("--loop", action="store_true", help="Run continuously in a loop")
    parser.add_argument("--interval-minutes", type=int, default=60, help="Interval in minutes between loop cycles")
    parser.add_argument("--dry-run", action="store_true", help="Perform refresh without writing status files or db rows")

    args = parser.parse_args()

    if args.loop:
        logger.info("Starting continuous data refresh daemon (interval: %d minutes)...", args.interval_minutes)
        while True:
            try:
                run_refresh_cycle(dry_run=args.dry_run)
            except Exception as err:
                logger.error("Error during scheduled refresh cycle: %s", err, exc_info=True)
            logger.info("Sleeping for %d minutes...", args.interval_minutes)
            time.sleep(args.interval_minutes * 60)
    else:
        # Default to running once
        run_refresh_cycle(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
