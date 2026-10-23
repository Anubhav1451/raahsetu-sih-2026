# Data freshness and versioning

RaahSetu separates source freshness from operational safety. A fresh source can
still be incomplete, and a benchmark record is never presented as a live
government closure.

## Current source states

| Source | Current state | Meaning |
|---|---|---|
| OpenStreetMap road snapshots | Versioned snapshot | Eight-state extracts are processed into immutable graph files and identified by content hash. |
| Open-Meteo forecast API | Live with 60-minute cache | Each weather response carries `fetched_at`, `fresh`, `stale` and `source`. |
| Hazard benchmark records | Versioned benchmark/fallback | Structured records support the demo workflow; they are not a live government incident feed. |
| NDMA SACHET adapter | Standby | Configure an authorised CAP feed before calling it live. |
| CWC flood adapter | Standby | Configure an authorised CWC endpoint before calling it live. |

## API contract

`GET /api/v1/data-status` returns the local audit timestamp, freshness policy,
source registry, runtime snapshots, counts and known gaps. `GET
/api/v1/hazards/live-feeds` reports configured feed status and returns no
synthetic advisories as if they were government warnings.

## Supabase registry

Migration `006_data_freshness.sql` creates `data_source_registry` and
`data_import_runs`. After applying migrations, run
`backend/scripts/register_data_sources.py` to register the current local
inventory. Import jobs should update the source row only after validation and
record a successful or failed run. A failed import must leave the previous
version available for rollback.

## Production update sequence

1. Fetch a source into a staging directory.
2. Validate schema, coordinates, timestamps and record counts.
3. Compute a content hash and create a new dataset version.
4. Import into an isolated versioned snapshot.
5. Run route and spatial-join smoke checks.
6. Mark the version active only after review.
7. Retain the previous version for rollback.
8. Expose `last_imported_at`, `valid_until`, source and review state in the UI.

Do not label a source `live` without an authorised endpoint, a successful
fetch timestamp and an auditable import record.
