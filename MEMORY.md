# Project Memory

## Current Status

RaahSetu is a working local SIH26002 MVP in `D:\FORSIH`. FastAPI runs on port 8000 and the React/R3F dashboard on port 5173. The dashboard supports synthetic, Guwahati OSM and provisional reviewed Guwahati corridor datasets, road/place search, route comparison, scenarios and an OSM SVG fallback when WebGL is unavailable.

## Recently Completed

- Eight Northeast state OSM road extracts and facility files acquired.
- Northeast coverage catalog with all eight states and capitals generated.
- Guwahati corridor snapshot created from two historical 1 km observations.
- Custom Risk-A* and 27-test verification suite established.
- Supabase/PostGIS schema, CSV imports and deployment manifests prepared.

## Known Problems and Limits

Supabase is connected; prior verification recorded three migrations, eight-state metadata, versioned pilot graphs and private evidence storage. Verified coordinate-level blackspot coverage is incomplete. Weather is reference-point data. Historical hazards are not current closures. Docker/Kubernetes execution and field validation remain pending.

## Recent Decisions

Risk belongs in edge cost; heuristic remains an admissible lower bound. Missing evidence is unknown. OSM graphs are prepared and loaded region-wise rather than all at once in the browser.

## Next Steps

1. Implement durable offline report and photo synchronization with account isolation and retry handling.
2. Add authenticated GPS vehicle tracking and delivery status.
3. Add alerts, district connectivity summaries and multilingual notifications.
4. Integrate permitted current weather feeds; train disruption prediction only after labelled-data validation.
5. Verify Docker/Kubernetes deployment and rehearse the full field-report-to-rerouting demo.

## September 7 security follow-up

Road-candidate lookup now checks the report's region before querying spatial matches.
Assigned reviewers cannot inspect another region; administrators retain cross-region access.
Missing reports return 404. Five API/store regression cases cover these boundaries.
The public GitHub repository is Anubhav1451/raahsetu-sih-2026.

## Session Handoff

Read `PRD.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/DATA.md`, `docs/COMPLETION-AUDIT.md` and `TESTING.md` before making a major change. Run `scripts\verify.ps1` after meaningful changes.
