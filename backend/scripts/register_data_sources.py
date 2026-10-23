"""Register source inventory and immutable import audit metadata in PostGIS."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    status = json.loads((ROOT / "datasets" / "DATA_STATUS.json").read_text(encoding="utf-8"))
    audited_at = status.get("audited_at")
    source_files = {
        "osm-road-snapshots": ROOT / "backend" / "data" / "osm-northeast.json",
        "hazard-benchmark": ROOT / "supabase" / "hazards-northeast-verified.csv",
    }
    sources = [
        ("osm-road-snapshots", "OpenStreetMap road graph snapshots", "OpenStreetMap", "road_network", "8 Northeast states", "fresh", status.get("runtime_pilot", {}).get("nodes", 0) + status.get("runtime_pilot", {}).get("directed_edges", 0), "versioned local snapshots"),
        ("open-meteo", "Open-Meteo forecast API", "Open-Meteo", "weather", "8 reference stations", "fresh", 8, "60-minute cache; fetched_at on each response"),
        ("hazard-benchmark", "Reviewed hazard benchmark records", "MoRTH/GSI/CWC/PWD categories", "hazards", "Selected Northeast corridors", "fallback", 24, "versioned import; not a live government feed"),
        ("ndma-sachet", "NDMA SACHET CAP adapter", "NDMA", "warnings", "Awaiting authorised feed", "standby", 0, "feed URL is not configured"),
        ("cwc-flood", "CWC flood forecast adapter", "CWC", "warnings", "Awaiting authorised feed", "standby", 0, "feed URL is not configured"),
    ]
    with psycopg.connect(url, sslmode=os.getenv("DATABASE_SSLMODE", "require")) as conn:
        for source_id, name, agency, kind, coverage, freshness, count, note in sources:
            source_file = source_files.get(source_id)
            content_hash = hashlib.sha256(source_file.read_bytes()).hexdigest() if source_file and source_file.exists() else None
            dataset_version = content_hash[:12] if content_hash else None
            conn.execute(
                """insert into data_source_registry
                (source_id,source_name,agency,source_kind,coverage,status,last_imported_at,
                 dataset_version,content_hash,record_count,review_status,metadata,updated_at)
                values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                on conflict(source_id) do update set source_name=excluded.source_name,
                agency=excluded.agency,source_kind=excluded.source_kind,coverage=excluded.coverage,
                status=excluded.status,last_imported_at=excluded.last_imported_at,
                dataset_version=excluded.dataset_version,content_hash=excluded.content_hash,
                record_count=excluded.record_count,metadata=excluded.metadata,updated_at=now()""",
                (source_id, name, agency, kind, coverage, freshness, audited_at, dataset_version,
                 content_hash, count, "reviewed" if source_id == "osm-road-snapshots" else "pending",
                 Jsonb({"note": note, "registered_at": datetime.now(UTC).isoformat()})),
            )
            if source_file and source_file.exists():
                conn.execute(
                    """insert into data_import_runs
                    (source_id,dataset_version,content_hash,completed_at,status,records_seen,metadata)
                    values(%s,%s,%s,now(),'succeeded',%s,%s)""",
                    (source_id, dataset_version, content_hash, count, Jsonb({"file": source_file.name})),
                )
    print(f"Registered {len(sources)} data sources and immutable import runs.")


if __name__ == "__main__":
    main()
