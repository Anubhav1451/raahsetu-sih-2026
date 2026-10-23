# RaahSetu storage architecture

RaahSetu uses a split storage model. Supabase/PostGIS is the operational cloud store for authentication, roles, reviewed incidents, alerts, fleet positions, delivery status, source registry and import audits. Complete OSM graphs, terrain archives, historical weather and other large immutable files remain in local PostGIS or versioned backend snapshots.

The routing service reads immutable graph snapshots locally and reads approved operational events from Supabase. A field report is only allowed to affect a future scoring snapshot after authority review. This keeps routing deterministic and prevents a free-tier database limit from becoming a routing failure.

`pgAdmin` is an administration interface; the local database itself is PostgreSQL with PostGIS. Local copies are backups or routing storage, not an automatic replica. Every import must record a dataset version, SHA-256 hash, source and import timestamp.
