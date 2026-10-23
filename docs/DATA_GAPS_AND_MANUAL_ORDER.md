# RaahSetu data completion order

## Already automated and verified

1. Eight-state OSM graph snapshots and route geometry.
2. SRTM terrain tiles and 2021–2025 weather archive.
3. Weather anomaly model with humidity and 2025 holdout.
4. Audited disruption model in advisory shadow mode.
5. Public-source catalog, candidate ingestion, RBAC and reviewer queue.
6. Redis cache/stream infrastructure with PostgreSQL/PostGIS as source of truth.

## Manual order still required

1. **Source verification:** open the official PDF/page and retain the exact URL,
   publication date and excerpt. Do not infer an incident start from publication.
2. **Location verification:** identify the exact road graph edge(s) and coordinates;
   record the matching method and distance. If the source has no chainage or
   coordinates, keep the candidate pending.
3. **Time semantics:** record incident start, restriction-effective and reopening
   times separately. Leave unknown values null.
4. **Outcome verification:** confirm blocked, restricted, reopened or unknown from
   an authority source. Conflicting reports remain quarantined.
5. **Reviewer action:** an authorized regional reviewer approves/rejects with an
   evidence note. Approval must satisfy the candidate validation rules.
6. **Label promotion:** only approved records can enter the training-label export;
   rerun the audit, date-grouped split and shadow evaluation afterward.
7. **Field pilot:** collect real GPS traces, weather at corridor coordinates, delay,
   detour and delivery outcomes. These are required before production safety or
   efficiency claims.
8. **External integrations:** obtain authorized NDMA/CWC/traffic endpoints, SMS/
   WhatsApp credentials and AIS-140/Traccar pilot access. Until then adapters stay
   in standby/simulator mode.

## Automatic monitoring additions

- `backend/app/model_drift.py` provides PSI-based feature drift signals with
  stable/watch/alert thresholds. It is advisory only and does not change routing.
- `backend.app.weather.interpolate_corridor_weather` attaches nearest-reference
  weather to route points while explicitly marking the result as an approximation,
  never as a corridor observation.

## Current measured gap

The validator currently reports 5 pending public candidates and 0 promotable
records. Their graph files exist, but verification and reviewer approval are still
missing. The disruption dataset contains 794 audited rows; it is not evidence that
all 794 are independently field-confirmed outcomes.
