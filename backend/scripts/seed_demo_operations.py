"""Seed realistic operations data (field reports and accessibility events) into PostgreSQL."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is not configured.")

with psycopg.connect(url, sslmode=os.getenv("DATABASE_SSLMODE", "require")) as conn:
    conn.execute("""
        insert into public.field_reports (
            client_report_id, region_code, district, place_name, kind,
            accessibility_status, severity, geom, description,
            observed_at, submitted_at, review_status, valid_until, details
        ) values
        (
            'rep-sela-pass-001', 'arunachal-pradesh', 'West Kameng', 'Sela Pass Summit Ridge',
            'landslide', 'blocked', 0.92, ST_SetSRID(ST_MakePoint(92.10, 27.50), 4326),
            'Active sub-zero rockfall and snow slush over NH-13. Heavy vehicles unable to pass summit bend. Detour via lower tunnel bypass recommended.',
            now() - interval '2 hours', now() - interval '1 hour', 'pending', now() + interval '22 hours',
            '{"has_photo": true, "reporter_role": "field_official", "district_sdma": "West Kameng DC Office"}'::jsonb
        ),
        (
            'rep-phesama-sink-002', 'nagaland', 'Kohima', 'NH-29 Phesama Subsidence Zone',
            'road_damage', 'restricted', 0.86, ST_SetSRID(ST_MakePoint(94.10, 25.65), 4326),
            'Tectonic sinking of road shoulder on NH-29. Multi-axle commercial freight halted; light emergency 4x4 permitted at 10km/h crawl.',
            now() - interval '4 hours', now() - interval '3 hours', 'pending', now() + interval '18 hours',
            '{"has_photo": true, "reporter_role": "field_official"}'::jsonb
        ),
        (
            'rep-sonapur-flood-003', 'meghalaya', 'East Jaintia Hills', 'Sonapur Tunnel Flash Mudflow',
            'flood', 'restricted', 0.88, ST_SetSRID(ST_MakePoint(92.36, 25.12), 4326),
            'Hill stream overflowed tunnel mouth; sludge clearance underway. Single lane alternating traffic.',
            now() - interval '6 hours', now() - interval '5 hours', 'pending', now() + interval '12 hours',
            '{"has_photo": true, "reporter_role": "field_official"}'::jsonb
        ),
        (
            'rep-nh10-teesta-004', 'sikkim', 'Pakyong', 'NH-10 29th Mile Teesta Sinking Section',
            'landslide', 'blocked', 0.95, ST_SetSRID(ST_MakePoint(88.51, 27.18), 4326),
            'Major debris slide blocked both carriageways of NH-10 near 29th Mile. Border Roads Organisation (BRO) deployed bulldozers. Estimated clearance time 12 hours.',
            now() - interval '3 hours', now() - interval '2 hours', 'pending', now() + interval '20 hours',
            '{"has_photo": true, "reporter_role": "field_official", "corridor": "NH-10"}'::jsonb
        )
        on conflict (client_report_id) do nothing;
    """)

    conn.execute("""
        insert into public.accessibility_events (
            region_code, dataset_id, edge_id, kind,
            accessibility_status, severity, geom, starts_at, ends_at, source, details
        ) values
        (
            'sikkim', 'osm-sikkim', 'edge-nh10-teesta-corridor-1', 'landslide',
            'blocked', 0.95, ST_SetSRID(ST_MakePoint(88.51, 27.18), 4326),
            now() - interval '2 hours', now() + interval '18 hours', 'promoted_report',
            '{"source_report_id": "rep-nh10-teesta-004", "restrictions": {"max_weight_tons": 0, "hazmat_prohibited": true}}'::jsonb
        ),
        (
            'nagaland', 'osm-nagaland', 'edge-nh29-phesama-sink-1', 'road_damage',
            'restricted', 0.82, ST_SetSRID(ST_MakePoint(94.10, 25.65), 4326),
            now() - interval '3 hours', now() + interval '24 hours', 'official_advisory',
            '{"restrictions": {"max_weight_tons": 16, "max_axles": 2}}'::jsonb
        )
        on conflict do nothing;
    """)
    conn.commit()
    print("Database successfully seeded with realistic operations data.")
