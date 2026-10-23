"""Recover the remote Supabase database after a disk-full event.

The complete road graphs are preserved in local PostGIS and the verified dump.
Remote Supabase is kept for metadata, hazards, field reports and auth; keeping
million-row road graphs there exceeds the free-tier disk budget. This script
therefore truncates only the graph tables, then removes their dataset metadata.
It deliberately leaves hazard observations, regions, reports, fleets, alerts,
and auth data untouched.

Usage (repo root):
    .venv/Scripts/python.exe scripts/recover_supabase_space.py
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def main() -> None:
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(
        url,
        connect_timeout=15,
        autocommit=True,
        options="-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("truncate table edge_hazard_reviews, road_edges, road_nodes")
            cur.execute("delete from dataset_versions where id like 'osm-%'")
            cur.execute("vacuum analyze road_edges")
            cur.execute("vacuum analyze road_nodes")
            cur.execute("select pg_database_size(current_database())")
            size_mb = cur.fetchone()[0] / 1024 / 1024
            print(f"database size now: {size_mb:.1f} MB (free-tier limit 500 MB)")
            cur.execute("select dataset_id, count(*) from road_edges group by dataset_id order by count(*) desc")
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]} edges")


if __name__ == "__main__":
    main()
